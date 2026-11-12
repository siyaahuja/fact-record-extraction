"""Load a PDF into pages: rendered image, text layer, garble repair, OCR, and word rows."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
from dataclasses import dataclass, field

import numpy as np
import pymupdf
from PIL import Image, ImageOps

from . import garble

OCR_VERSION = "v2"
RENDER_DPI = 150
OCR_DPI = 300


@dataclass
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class Row:
    """Words on one visual line, left to right, with coordinates in PDF points."""
    words: list[Word]
    source: str

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class Page:
    page_no: int
    width: float
    height: float
    image_path: str
    pdf_text: str
    text_status: str  # none | sparse | garbled | partial_garbled | good
    garbled_ratio: float
    repaired_text: str
    ocr_text: str
    rows: list[Row] = field(default_factory=list)

    def sources(self) -> dict[str, str]:
        """Every text rendering of this page, used for rules extraction and quote validation."""
        out = {}
        if self.text_status in ("good", "partial_garbled", "sparse"):
            out["pdf_text"] = self.pdf_text
        if self.garbled_ratio > 0:
            out["repaired_text"] = self.repaired_text
        if self.ocr_text.strip():
            out["ocr"] = self.ocr_text
        return out

    def best_text(self) -> str:
        if self.text_status == "good":
            return self.pdf_text
        if self.text_status == "partial_garbled":
            return self.repaired_text + "\n\n[OCR]\n" + self.ocr_text
        return self.ocr_text


@dataclass
class Document:
    path: str
    sha256: str
    metadata: dict
    pages: list[Page]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def text_status(text: str, garbled_ratio: float) -> str:
    alnum = len(re.findall(r"[A-Za-z0-9]", text))
    if alnum < 40:
        return "none"
    if garbled_ratio > 0.5:
        return "garbled"
    if garbled_ratio > 0.02:
        return "partial_garbled"
    return "good"


def _rows_from_words(words: list[Word], source: str) -> list[Row]:
    """Group words into visual rows by vertical overlap (keeps table cells on one row)."""
    rows: list[list[Word]] = []
    for w in sorted(words, key=lambda w: ((w.y0 + w.y1) / 2, w.x0)):
        yc = (w.y0 + w.y1) / 2
        if rows:
            last = rows[-1]
            ly = sum((v.y0 + v.y1) / 2 for v in last) / len(last)
            lh = max(v.y1 - v.y0 for v in last)
            if abs(yc - ly) < 0.5 * max(lh, w.y1 - w.y0):
                last.append(w)
                continue
        rows.append([w])
    return [Row(sorted(r, key=lambda w: w.x0), source) for r in rows]


def _dark_bands(gray: Image.Image, frac: float = 0.6, lum: int = 128, min_h: int = 20, merge_gap: int = 60):
    a = np.asarray(gray)
    dark = (a < lum).mean(axis=1) > frac
    bands, start = [], None
    for y, d in enumerate(list(dark) + [False]):
        if d and start is None:
            start = y
        if not d and start is not None:
            if y - start >= min_h:
                if bands and start - bands[-1][1] < merge_gap:
                    bands[-1] = (bands[-1][0], y)
                else:
                    bands.append((start, y))
            start = None
    return bands


def _ocr(gray: Image.Image, scale: float) -> tuple[str, list[Word]]:
    """OCR the page normally, then each full-width dark band inverted (white-on-dark banners)."""
    import pytesseract

    texts = [pytesseract.image_to_string(gray, config="--psm 3")]
    words: list[Word] = []

    def collect(img: Image.Image, dy: int, psm: int):
        data = pytesseract.image_to_data(img, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
        for i, t in enumerate(data["text"]):
            if t.strip() and float(data["conf"][i]) > 30:
                x, y, w, h = data["left"][i], data["top"][i] + dy, data["width"][i], data["height"][i]
                words.append(Word(t.strip(), x / scale, y / scale, (x + w) / scale, (y + h) / scale))

    collect(gray, 0, 3)
    for y0, y1 in _dark_bands(gray):
        y0, y1 = max(0, y0 - 5), min(gray.height, y1 + 5)
        band = ImageOps.invert(gray.crop((0, y0, gray.width, y1)))
        texts.append(pytesseract.image_to_string(band, config="--psm 11"))
        collect(band, y0, 11)
    return "\n\n".join(t.strip() for t in texts if t.strip()), _dedupe(words)


def _overlap(a: Word, b: Word) -> float:
    ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    area = min((a.x1 - a.x0) * (a.y1 - a.y0), (b.x1 - b.x0) * (b.y1 - b.y0)) or 1.0
    return ix * iy / area


def _dedupe(words: list[Word]) -> list[Word]:
    kept: list[Word] = []
    for w in words:
        if not any(_overlap(w, k) > 0.5 for k in kept):
            kept.append(w)
    return kept


def load_document(path: str, cache_dir: str = ".cache", ocr: bool = True) -> Document:
    sha = sha256_file(path)
    doc = pymupdf.open(path)
    img_dir = os.path.join(cache_dir, "pages", sha[:16])
    ocr_dir = os.path.join(cache_dir, "ocr")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(ocr_dir, exist_ok=True)
    pages = []
    for p in doc:
        n = p.number + 1
        img_path = os.path.join(img_dir, f"p{n}.png")
        if not os.path.exists(img_path):
            p.get_pixmap(dpi=RENDER_DPI).save(img_path)
        raw = p.get_text()
        g = garble.analyse(raw)
        status = text_status(raw, g["garbled_ratio"])
        pdf_words = [Word(w[4], w[0], w[1], w[2], w[3]) for w in p.get_text("words")]
        rows = _rows_from_words(pdf_words, "pdf_text") if status in ("good", "partial_garbled") else []

        ocr_text = ""
        if ocr:
            cache = os.path.join(ocr_dir, f"{sha[:16]}_p{n}_{OCR_VERSION}.json")
            if os.path.exists(cache):
                with open(cache) as f:
                    c = json.load(f)
                ocr_text, ocr_words = c["text"], [Word(**w) for w in c["words"]]
            else:
                scale = OCR_DPI / 72
                gray = Image.open(io.BytesIO(p.get_pixmap(dpi=OCR_DPI).tobytes("png"))).convert("L")
                ocr_text, ocr_words = _ocr(gray, scale)
                with open(cache, "w") as f:
                    json.dump({"text": ocr_text, "words": [w.__dict__ for w in ocr_words]}, f)
            pdf_alnum = len(re.findall(r"[A-Za-z0-9]", raw))
            if status == "good" and pdf_alnum < 0.25 * len(re.findall(r"[A-Za-z0-9]", ocr_text)):
                status = "sparse"
            if status != "good":
                rows += _rows_from_words(ocr_words, "ocr")

        pages.append(Page(
            page_no=n, width=p.rect.width, height=p.rect.height, image_path=img_path,
            pdf_text=raw, text_status=status, garbled_ratio=g["garbled_ratio"],
            repaired_text=g["repaired_text"], ocr_text=ocr_text, rows=rows,
        ))
    return Document(path=path, sha256=sha, metadata=dict(doc.metadata or {}), pages=pages)
