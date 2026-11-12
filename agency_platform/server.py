"""Agency review platform API. Run from the repo root: python -m uvicorn agency_platform.server:app"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from collections import Counter
from pathlib import Path

import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from extraction.pipeline import run as run_extraction

from . import contracts_gen as cg

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("AGENCY_DATA_DIR", HERE / "data"))
SAMPLE = ROOT / "sample_data"
PUBLISH_DIR = Path(os.environ.get("AGENCY_PUBLISH_DIR", ROOT / "out"))
CACHE = str(ROOT / ".cache")
LOCK = threading.Lock()

app = FastAPI(title="Agency Review Platform")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _read(p: Path, default=None):
    if not p.exists():
        return default
    if p.suffix == ".jsonl":
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return json.loads(p.read_text())


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    tmp.replace(p)


def dev_dir(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", slug) or not (DATA / slug).is_dir():
        raise HTTPException(404, f"unknown development {slug}")
    return DATA / slug


def extract(slug: str) -> None:
    d = DATA / slug
    with LOCK:
        run_extraction(str(d / "docs"), str(d / "out"), extractor="rules", cache_dir=CACHE, log=lambda *_: None)
    rebuild(slug)


def rebuild(slug: str) -> dict:
    d = DATA / slug
    docs = _read(d / "out" / "documents.jsonl", [])
    facts = _read(d / "out" / "facts.jsonl", [])
    contradictions = _read(d / "out" / "contradictions.jsonl", [])
    meta = _read(d / "meta.json", {})
    dev_ids = Counter(x.get("development_id") for x in docs if x.get("development_id"))
    units = Counter(x.get("unit_id") for x in docs if x.get("unit_id"))
    meta["development_id"] = dev_ids.most_common(1)[0][0] if dev_ids else slug
    meta["name"] = next((x["development_name"] for x in docs if x.get("development_name")), meta.get("name", slug))
    meta["primary_unit_id"] = units.most_common(1)[0][0] if units else None
    _write(d / "meta.json", meta)
    labels = cg.label_contradictions(contradictions, _read(SAMPLE / "contradictions.json"))
    extracted = cg.build_extracted({"slug": slug, **meta}, docs, facts, contradictions, labels)
    actions = _read(d / "contracts" / "02_review_actions.json", None) or {
        "contract": "02_review_actions", "development_id": meta["development_id"], "actions": []}
    resolved = cg.build_resolved(extracted, actions["actions"])
    voice = cg.build_voice(resolved, extracted, meta["primary_unit_id"])
    listing = cg.build_listing(resolved, extracted, meta["primary_unit_id"])
    c = d / "contracts"
    _write(c / "01_extracted.json", extracted)
    _write(c / "02_review_actions.json", actions)
    _write(c / "03_resolved.json", resolved)
    _write(c / "04_voice_agent.json", voice)
    _write(c / "05_listing.json", listing)
    return resolved


def seed() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for src in sorted(p for p in SAMPLE.iterdir() if p.is_dir()):
        d = DATA / src.name
        if not (d / "docs").exists():
            (d / "docs").mkdir(parents=True)
            for pdf in src.glob("*.pdf"):
                shutil.copy(pdf, d / "docs" / pdf.name)
            _write(d / "meta.json", {"slug": src.name, "name": src.name.replace("-", " ").title(), "seeded_from": f"sample_data/{src.name}"})
        if (SAMPLE / "manifest.json").exists():
            shutil.copy(SAMPLE / "manifest.json", d / "docs" / "manifest.json")
        if not (d / "out" / "facts.jsonl").exists():
            extract(src.name)
        else:
            rebuild(src.name)


@app.on_event("startup")
def _startup():
    seed()


def contract(slug: str, n: str) -> dict:
    names = {"01": "01_extracted", "02": "02_review_actions", "03": "03_resolved", "04": "04_voice_agent", "05": "05_listing"}
    p = dev_dir(slug) / "contracts" / f"{names[n]}.json"
    if not p.exists():
        rebuild(slug)
    return _read(p)


def summary(slug: str) -> dict:
    meta = _read(dev_dir(slug) / "meta.json", {})
    res = contract(slug, "03")
    ext = contract(slug, "01")
    live = [f for f in res["facts"] if f["status"] != "rejected"]
    verified = [f for f in live if f["status"] == "verified"]
    return {"slug": slug, **meta, "documents": len(ext["documents"]), "facts": len(res["facts"]),
            "rejected_facts": len(res["facts"]) - len(live),
            "open_contradictions": sum(c["status"] == "open" for c in res["contradictions"]),
            "contradictions": len(res["contradictions"]),
            "verified_pct": round(100 * len(verified) / len(live)) if live else 0,
            "published": (PUBLISH_DIR / "listings" / f"{slug}.json").exists()}


@app.get("/api/developments")
def list_developments():
    return [summary(p.name) for p in sorted(DATA.iterdir()) if p.is_dir() and (p / "meta.json").exists()]


class NewDev(BaseModel):
    name: str


@app.post("/api/developments")
def create_development(body: NewDev):
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")
    if not slug or (DATA / slug).exists():
        raise HTTPException(400, "invalid or existing name")
    (DATA / slug / "docs").mkdir(parents=True)
    if (SAMPLE / "manifest.json").exists():
        shutil.copy(SAMPLE / "manifest.json", DATA / slug / "docs" / "manifest.json")
    _write(DATA / slug / "meta.json", {"slug": slug, "name": body.name})
    return {"slug": slug, "name": body.name}


@app.get("/api/developments/{slug}")
def get_development(slug: str):
    return summary(slug)


@app.post("/api/developments/{slug}/documents")
async def upload(slug: str, files: list[UploadFile] = File(...)):
    d = dev_dir(slug)
    saved = []
    for f in files:
        name = Path(f.filename or "upload.pdf").name
        if not name.lower().endswith(".pdf"):
            raise HTTPException(400, f"{name}: only PDFs are accepted")
        (d / "docs" / name).write_bytes(await f.read())
        saved.append(name)
    extract(slug)
    return {"uploaded": saved, **summary(slug)}


@app.get("/api/developments/{slug}/documents")
def documents(slug: str):
    return contract(slug, "01")["documents"]


@app.get("/api/developments/{slug}/facts")
def facts(slug: str):
    return contract(slug, "03")["facts"]


@app.get("/api/developments/{slug}/contradictions")
def contradictions(slug: str):
    return contract(slug, "03")["contradictions"]


def _doc_path(slug: str, doc_id: str) -> Path:
    doc = next((x for x in contract(slug, "01")["documents"] if x["doc_id"] == doc_id), None)
    if not doc:
        raise HTTPException(404, "unknown document")
    p = dev_dir(slug) / "docs" / Path(doc["file_uri"]).name
    if not p.exists():
        raise HTTPException(404, "file missing")
    return p


@app.get("/api/developments/{slug}/documents/{doc_id}/file")
def doc_file(slug: str, doc_id: str):
    return FileResponse(_doc_path(slug, doc_id), media_type="application/pdf")


@app.get("/api/developments/{slug}/documents/{doc_id}/pages/{page}.png")
def page_image(slug: str, doc_id: str, page: int, quote: str | None = None):
    src = _doc_path(slug, doc_id)
    key = uuid.uuid5(uuid.NAMESPACE_URL, f"{src.stat().st_mtime}|{page}|{quote or ''}").hex[:16]
    out = dev_dir(slug) / "pages" / f"{doc_id}-p{page}-{key}.png"
    if not out.exists():
        doc = fitz.open(src)
        if not 1 <= page <= doc.page_count:
            raise HTTPException(404, "no such page")
        pg = doc[page - 1]
        hits = []
        if quote:
            hits = pg.search_for(quote[:60]) or pg.search_for(quote.split("\n")[0][:30])
            for r in hits:
                annot = pg.add_highlight_annot(r)
                annot.set_colors(stroke=(1, 0.85, 0.2))
                annot.update()
        out.parent.mkdir(parents=True, exist_ok=True)
        pix = pg.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), annots=True)
        if quote and not hits:
            _ocr_highlight(pix, quote).save(out)
        else:
            pix.save(out)
    return FileResponse(out, media_type="image/png")


def _norm_tok(s: str) -> str:
    return re.sub(r"[^a-z0-9£]", "", s.lower())


def _ocr_highlight(pix, quote: str):
    """Scanned pages have no text layer: find the quote's words in Tesseract's word boxes and box them."""
    from PIL import Image, ImageDraw
    import pytesseract
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
    q = [t for t in (_norm_tok(w) for w in quote.split()) if t]
    if not q:
        return img
    try:
        data = pytesseract.image_to_data(img.convert("RGB"), output_type=pytesseract.Output.DICT, timeout=30)
    except Exception:
        return img
    words = [(i, _norm_tok(t)) for i, t in enumerate(data["text"]) if _norm_tok(t)]
    best, best_i = 0, None
    for s in range(len(words)):
        score = sum(1 for k in range(min(len(q), len(words) - s)) if words[s + k][1] == q[k])
        if score > best:
            best, best_i = score, s
    if best_i is None or best < max(1, len(q) * 0.5):
        return img
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for k in range(min(len(q), len(words) - best_i)):
        i = words[best_i + k][0]
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        draw.rectangle([x - 3, y - 3, x + w + 3, y + h + 3], fill=(255, 210, 40, 110), outline=(230, 150, 0, 255), width=2)
    return Image.alpha_composite(img, overlay).convert("RGB")


class ReviewAction(BaseModel):
    action: str
    fact_id: str | None = None
    contradiction_id: str | None = None
    resolution: str | None = None
    chosen_fact_id: str | None = None
    reviewer: str = "agency-reviewer"
    reason: str | None = None


@app.post("/api/developments/{slug}/review-actions")
def review_action(slug: str, a: ReviewAction):
    d = dev_dir(slug)
    ext = contract(slug, "01")
    fact_ids = {f["fact_id"] for f in ext["facts"]}
    cons = {c["contradiction_id"]: c for c in ext["contradictions"]}
    labels = {c["label"]: c["contradiction_id"] for c in ext["contradictions"] if c.get("label")}
    if a.contradiction_id in labels:
        a.contradiction_id = labels[a.contradiction_id]
    if a.action in ("reject_fact", "unreject_fact"):
        if a.fact_id not in fact_ids:
            raise HTTPException(400, "unknown fact_id")
    elif a.action == "resolve_contradiction":
        c = cons.get(a.contradiction_id)
        if not c:
            raise HTTPException(400, "unknown contradiction_id")
        if a.resolution not in ("choose_fact", "accept_recommendation", "keep_both_scoped"):
            raise HTTPException(400, "resolution must be choose_fact | accept_recommendation | keep_both_scoped")
        if a.resolution == "choose_fact" and a.chosen_fact_id not in c["fact_ids"]:
            raise HTTPException(400, "chosen_fact_id must be one of the contradiction's fact_ids")
    elif a.action == "reopen_contradiction":
        if a.contradiction_id not in cons:
            raise HTTPException(400, "unknown contradiction_id")
    else:
        raise HTTPException(400, "unknown action")
    actions = contract(slug, "02")
    entry = {"action_id": str(uuid.uuid4()), **{k: v for k, v in a.model_dump().items() if v is not None},
             "timestamp": cg.now()}
    actions["actions"].append(entry)
    _write(d / "contracts" / "02_review_actions.json", actions)
    rebuild(slug)
    return {"recorded": entry, **summary(slug)}


@app.get("/api/developments/{slug}/review-actions")
def get_actions(slug: str):
    return contract(slug, "02")


@app.get("/api/developments/{slug}/extracted")
def get_extracted(slug: str):
    return contract(slug, "01")


@app.get("/api/developments/{slug}/resolved")
def get_resolved(slug: str):
    return contract(slug, "03")


@app.get("/api/developments/{slug}/voice-agent")
def get_voice(slug: str):
    return contract(slug, "04")


@app.get("/api/developments/{slug}/listing")
def get_listing(slug: str):
    return contract(slug, "05")


@app.post("/api/developments/{slug}/publish")
def publish(slug: str):
    rebuild(slug)
    listing, voice = contract(slug, "05"), contract(slug, "04")
    lp, vp = PUBLISH_DIR / "listings" / f"{slug}.json", PUBLISH_DIR / "voice" / f"{slug}.json"
    _write(lp, listing)
    _write(vp, voice)
    return {"listing_path": str(lp.relative_to(ROOT) if lp.is_relative_to(ROOT) else lp),
            "voice_path": str(vp.relative_to(ROOT) if vp.is_relative_to(ROOT) else vp), "published_at": cg.now()}


DIST = HERE / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "not found"}, status_code=404)
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
