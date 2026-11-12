"""Gatekeeper for every candidate fact, from rules or from the LLM.

A fact is rejected if its field or qualifier is unknown, its page doesn't exist, its quote can't be
found in that page's text layer / repaired text / OCR / layout rows, or its value isn't printed
in its own value_raw and quote. Area normalisation and doc_error are recomputed here, never trusted.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from .catalogue import (AVAILABILITY, EPC_BANDS, FIELDS, PARKING_KINDS, SQ_M_TO_SQ_FT, TENURES,
                        TRANSACTION_TYPES)
from .pdfio import Page
from .units import is_doc_error, normalise_area, parse_number, unit_pair_mismatch

SCOPE_RE = r"whole|unit|(floor|part|house_type|plot):[a-z0-9_]+"


def squash(s: str) -> str:
    return re.sub(r"[^a-z0-9£]", "", (s or "").lower())


def page_haystacks(page: Page) -> dict[str, str]:
    hay = {name: squash(text) for name, text in page.sources().items()}
    hay["layout_rows"] = squash("\n".join(r.text for r in page.rows))
    return hay


def find_quote(quote: str, hay: dict[str, str]) -> tuple[str | None, str]:
    q = squash(quote)
    if len(q) < 4:
        return None, "quote_too_short"
    for name, h in hay.items():
        if q in h:
            return name, "exact"
    # OCR noise ("Grade Il", "c¢.90"): accept a near-exact match on OCR text, but only isolated 1-2 character
    # slips that touch no digit, so an inserted word ("not") or a changed number never validates.
    for name in ("ocr", "layout_rows", "repaired_text"):
        h = hay.get(name)
        if h and len(q) >= 12 and fuzz.partial_ratio(q, h) >= 92 and _ocr_slips_only(q, h, quote):
            return name, "fuzzy"
    return None, "quote_not_found"


def _ocr_slips_only(q: str, h: str, quote: str) -> bool:
    al = fuzz.partial_ratio_alignment(q, h)
    win = h[max(0, al.dest_start - 6):al.dest_end + 6]
    ops = [op for op in Levenshtein.opcodes(q, win) if op.tag != "equal"]
    # Window slack at either end shows up as leading/trailing inserts.
    while ops and ops[0].tag == "insert" and ops[0].src_start == 0:
        ops.pop(0)
    while ops and ops[-1].tag == "insert" and ops[-1].src_start == len(q):
        ops.pop()
    edits = 0
    for op in ops:
        a, b = q[op.src_start:op.src_end], win[op.dest_start:op.dest_end]
        if max(len(a), len(b)) > 2 or re.search(r"\d", a + b):
            return False
        edits += max(len(a), len(b))
    if edits > max(2, len(q) // 12):
        return False
    # The aligner can scatter an inserted word into single-character edits, so check words too.
    for w in set(re.findall(r"[a-z]{3,}", quote.lower())):
        if w not in win and not (len(w) >= 5 and fuzz.partial_ratio(w, win) >= 80):
            return False
    return True


def _numbers(s: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", s or "")]


def _num_in(amount: float, text: str) -> bool:
    nums = _numbers(text)
    words = re.findall(r"[a-z]+", (text or "").lower())
    if any(abs(n - amount) <= max(0.01, 0.0005 * amount) for n in nums):
        return True
    if any(abs(n * 1e6 - amount) < 1 or abs(n * 1e3 - amount) < 1 for n in nums):
        return True
    return any(parse_number(w) == amount for w in words)


def check_qualifier(field: str, qualifier: dict) -> str | None:
    allowed = FIELDS[field]
    for k, v in qualifier.items():
        if k not in allowed:
            return f"unknown_qualifier_key:{k}"
        if k == "scope" and field in ("floor_area", "availability"):
            if not re.fullmatch(SCOPE_RE, str(v)):
                return f"bad_scope:{v}"
        elif allowed[k] is not None and v not in allowed[k]:
            return f"bad_qualifier_value:{k}={v}"
    return None


def check_value(field: str, f: dict) -> str | None:
    v, raw, quote = f["value"], f["value_raw"], f["quote"]
    sq_raw, sq_quote = squash(raw), squash(quote)
    if sq_raw and sq_raw not in sq_quote and fuzz.partial_ratio(sq_raw, sq_quote) < 90:
        return "value_raw_not_in_quote"
    if field in ("price", "rent", "ground_rent", "service_charge"):
        if not isinstance(v.get("amount"), (int, float)) or not _num_in(v["amount"], raw):
            return "amount_not_printed"
    elif field == "floor_area":
        if v.get("unit") not in ("sq_ft", "sq_m") or not _num_in(v.get("amount", -1), raw):
            return "area_not_printed"
        p = f.get("paired")
        if p and not _num_in(p.get("amount", -1), quote):
            return "paired_area_not_printed"
    elif field == "epc_rating":
        if v.get("band") not in EPC_BANDS or not re.search(rf"(?<![A-Za-z]){re.escape(v['band'])}(?![a-z])", raw):
            return "band_not_printed"
    elif field == "tenure":
        if v.get("tenure") not in TENURES or squash(v["tenure"].replace("_", " ")) not in sq_quote:
            return "tenure_not_printed"
    elif field == "transaction_type":
        if v.get("type") not in TRANSACTION_TYPES:
            return "bad_transaction_type"
    elif field == "parking":
        if not isinstance(v.get("spaces"), int) or not _num_in(v["spaces"], raw):
            return "spaces_not_printed"
        if v.get("kind", "unspecified") not in PARKING_KINDS:
            return "bad_parking_kind"
    elif field == "availability":
        if v.get("status") not in AVAILABILITY:
            return "bad_availability"
    elif field in ("bedrooms", "bathrooms"):
        if not isinstance(v.get("count"), int) or not _num_in(v["count"], raw):
            return "count_not_printed"
    return None


def finalise_area(f: dict) -> None:
    v = f["value"]
    f["normalised"] = normalise_area(v["amount"], v["unit"])
    f["doc_error"] = False
    p = f.pop("paired", None)
    if p and p.get("unit") in ("sq_ft", "sq_m") and p["unit"] != v["unit"]:
        sq_ft = v["amount"] if v["unit"] == "sq_ft" else p["amount"]
        sq_m = v["amount"] if v["unit"] == "sq_m" else p["amount"]
        mismatch = unit_pair_mismatch(sq_ft, sq_m)
        f["unit_check"] = {
            "printed_sq_ft": sq_ft, "printed_sq_m": sq_m,
            "sq_m_as_sq_ft": round(sq_m * SQ_M_TO_SQ_FT, 1), "mismatch_pct": round(100 * mismatch, 1),
        }
        f["doc_error"] = is_doc_error(sq_ft, sq_m)


def validate(f: dict, pages: dict[int, Page], hay_cache: dict[int, dict]) -> tuple[dict | None, str | None]:
    field = f.get("field")
    if field not in FIELDS:
        return None, f"unknown_field:{field}"
    page = pages.get(f.get("page"))
    if page is None:
        return None, "no_such_page"
    f["qualifier"] = {k: v for k, v in (f.get("qualifier") or {}).items() if v is not None}
    f["value"] = {k: v for k, v in (f.get("value") or {}).items() if v is not None}
    err = check_qualifier(field, f["qualifier"])
    if err:
        return None, err
    if page.page_no not in hay_cache:
        hay_cache[page.page_no] = page_haystacks(page)
    src, how = find_quote(f.get("quote") or "", hay_cache[page.page_no])
    if src is None:
        return None, how
    f["quote_source"], f["quote_match"] = src, how
    err = check_value(field, f)
    if err:
        return None, err
    if field == "floor_area":
        f.setdefault("qualifier", {}).setdefault("basis", "unspecified")
        f["qualifier"].setdefault("scope", "whole")
        finalise_area(f)
    else:
        f.pop("paired", None)
        f["normalised"] = None
        f["doc_error"] = bool(f.get("doc_error", False))
    return f, None
