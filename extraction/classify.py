"""Document-level classification: issuer, doc_type, dates, doc_id, subject address and focus floor."""
from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime

from .catalogue import DOC_TYPE_TIER
from .pdfio import Document
from .rules import FLOOR_RE, floor_slug

KNOWN_ISSUERS = [
    (r"HM\s+Land\s+Registry", "HM Land Registry", "official_register"),
    (r"Carter\s*Jonas", "Carter Jonas", "sales_agent"),
    (r"Strutt\s*(?:&|and)\s*Parker", "Strutt & Parker", "sales_agent"),
    (r"Savills", "Savills", "sales_agent"),
    (r"Knight\s+Frank", "Knight Frank", "sales_agent"),
    (r"Hamptons", "Hamptons", "sales_agent"),
    (r"Foxtons", "Foxtons", "sales_agent"),
    (r"Rightmove", "Rightmove", "sales_agent"),
    (r"Zoopla", "Zoopla", "sales_agent"),
    (r"OnTheMarket", "OnTheMarket", "sales_agent"),
    (r"NHBC", "NHBC", "warranty_provider"),
]

DOC_TYPE_CUES = {
    "epc_certificate": [(r"energy\s+performance\s+certificate", 3), (r"certificate\s+number", 2), (r"valid\s+until", 1), (r"energy\s+rating", 1)],
    "land_registry_title_extract": [(r"land\s+registry", 3), (r"title\s+number", 3), (r"register\s+of\s+title", 3), (r"proprietorship\s+register", 2)],
    "measured_survey": [(r"measured\s+(building\s+)?survey", 4), (r"schedule\s+of\s+areas", 2), (r"code\s+of\s+measuring\s+practice", 3)],
    "parking_allocation_schedule": [(r"parking\s+allocation\s+schedule", 6), (r"allocated\s+to", 1)],
    "schedule_of_finishes": [(r"schedule\s+of\s+finishes", 6), (r"specification", 1)],
    "signed_specification": [(r"signed\s+specification", 5)],
    "developer_instruction": [(r"formal\s+instruction", 4), (r"instruct\s+you", 2), (r"amend(ment)?\s+(to\s+)?(the\s+)?guide\s+price", 3), (r"price\s+change", 2)],
    "price_list_signed": [(r"price\s+list", 4)],
    "portal_listing": [(r"listing\s+id", 3), (r"captured", 1), (r"added\s+on", 2), (r"portal", 1), (r"listing\s+information", 2)],
    "lease": [(r"this\s+lease\s+is\s+made", 6), (r"term\s+commencement\s+date", 3)],
    "particulars": [(r"particulars", 2), (r"viewings?", 1), (r"sole\s+agents?", 2), (r"guide\s+price", 1), (r"accommodation", 1), (r"important\s+notice", 1)],
    "brochure": [(r"\bbrochure\b", 3)],
}

MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
DATE_RE = rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS}|sept?)\.?\s+(\d{{4}})"
NAME_RE = (r"\b(?:(\d{1,4})\s+)?((?:St\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+"
           r"(?:Close|Road|Street|Lane|Avenue|Drive|Way|Place|Gardens|Square|Crescent|Villa|House|Court|Mews|Terrace|Park))\b")
BUILDING_SUFFIX = r"(Villa|House|Court|Mews)$"
POSTCODE_RE = r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b"


def _parse_date(text: str) -> str | None:
    m = re.search(DATE_RE, text, re.I)
    if m:
        mon = m.group(2).lower()[:3]
        try:
            return datetime.strptime(f"{m.group(1)} {mon} {m.group(3)}", "%d %b %Y").date().isoformat()
        except ValueError:
            return None
    m = re.search(r"\b(\d{2})[/.](\d{2})[/.](\d{4})\b", text)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
        except ValueError:
            return None
    return None


def _all_text(doc: Document) -> str:
    return "\n\n".join(p.best_text() if p.text_status != "good" else p.pdf_text for p in doc.pages)


def guess_doc_type(text: str) -> tuple[str, dict]:
    scores = {t: sum(w for rx, w in cues if re.search(rx, text, re.I)) for t, cues in DOC_TYPE_CUES.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "particulars"
    return best, {k: v for k, v in scores.items() if v}


def find_issuer(doc: Document, text: str, doc_type: str) -> tuple[str | None, str | None]:
    if doc_type == "epc_certificate":
        return "EPC register", "official_register"
    if doc_type == "land_registry_title_extract":
        return "HM Land Registry", "official_register"
    first = doc.pages[0].pdf_text if doc.pages[0].text_status == "good" else doc.pages[0].ocr_text
    lines = [l.strip() for l in first.splitlines() if l.strip()][:4]
    role_by_type = {"measured_survey": "architect", "schedule_of_finishes": "developer", "signed_specification": "developer",
                    "parking_allocation_schedule": "managing_agent", "price_list_signed": "developer"}
    if doc_type == "portal_listing":
        m = re.search(r"https?://(?:www\.)?([a-z0-9-]+)\.", text)
        if m:
            return m.group(1).replace("-", " ").title(), None
    if doc_type not in ("particulars", "brochure", "portal_listing"):
        for i, line in enumerate(lines):
            if re.search(r"\b(Ltd|Limited|LLP|plc)\b", line) and len(line) < 60:
                if i > 0 and len(lines[i - 1]) < 30 and lines[i - 1].isupper():
                    line = f"{lines[i - 1].title()} {line}"
                role = "conveyancer" if re.search(r"solicitor", first, re.I) else role_by_type.get(doc_type, "developer")
                return line, role
        if lines and len(lines[0]) < 45 and (lines[0].isupper() or "&" in lines[0]):
            return lines[0].title().replace("&", "&"), role_by_type.get(doc_type, "developer")
    for rx, name, role in KNOWN_ISSUERS:
        if re.search(rx, text, re.I):
            if role == "sales_agent" and re.search(r"\bto\s+let\b", text[:600], re.I) and not re.search(r"for\s+sale", text[:600], re.I):
                role = "letting_agent"
            return name, role
    return None, None


def find_dates(doc: Document, text: str, doc_type: str) -> dict:
    out = {"doc_date": None, "doc_date_source": None, "register_date": None}
    meta = (doc.metadata or {}).get("creationDate", "")
    meta_date = None
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", meta)
    if m:
        meta_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    reg = re.search(r"(?:register\s+checked|search\s+date(?:\s+and\s+time)?)\s*:?\s*\n?\s*" + DATE_RE, text, re.I)
    if reg:
        out["register_date"] = _parse_date(reg.group(0))
    labelled = [
        (r"date\s+of\s+certificate\s*\n?\s*", "register" if doc_type == "epc_certificate" else "printed"),
        (r"search\s+date(?:\s+and\s+time)?\s*:?\s*", "register"),
        (r"\bdate\s*:\s*", "printed"),
        (r"\beffective\s+", "printed"),
        (r"\bissued\s*\n?\s*", "printed"),
        (r"captured\s+", "printed"),
        (r"rev\s+[a-z]\s+·\s+", "printed"),
    ]
    for rx, src in labelled:
        m = re.search(rx + rf"({DATE_RE}|\d{{2}}/\d{{2}}/\d{{4}})", text, re.I)
        if m:
            out["doc_date"], out["doc_date_source"] = _parse_date(m.group(1)), src
            return out
    m = re.search(rf"particulars\s+prepared\s+({MONTHS})\s*(\d{{4}})?", text, re.I)
    if m:
        month = datetime.strptime(m.group(1)[:3], "%b").month
        year = m.group(2) or (meta_date[:4] if meta_date else None)
        if year:
            out["doc_date"] = f"{year}-{month:02d}"
            out["doc_date_source"] = "printed" if m.group(2) else "printed+file_metadata"
            return out
    head = "\n".join(text.splitlines()[:12])
    d = _parse_date(head)
    if d:
        out["doc_date"], out["doc_date_source"] = d, "printed"
        return out
    if meta_date:
        out["doc_date"], out["doc_date_source"] = meta_date, "file_metadata"
    return out


def make_doc_id(path: str, sha: str, registry: dict[str, str]) -> str:
    if sha in registry:
        return registry[sha]
    stem = os.path.splitext(os.path.basename(path))[0]
    m = re.search(r"([a-z]+)-([0-9a-f]{8})$", stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return f"{re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')[:40]}-{sha[:8]}"


def address_candidates(text: str) -> list[dict]:
    out = []
    for m in re.finditer(NAME_RE, text):
        name = re.sub(r"\s+", " ", m.group(2))
        after = text[m.end():m.end() + 70]
        pc = re.search(POSTCODE_RE, after)
        town = re.match(r"\s*[,\n]\s*(?:[A-Z][\w ]*(?:Road|Street|Lane)\s*[,\n]\s*)?([A-Za-z][A-Za-z ]{2,25}?)(?:\s*[,\n(]|\s+[A-Z]{1,2}\d)", after)
        out.append({
            "name": name, "number": m.group(1),
            "postcode": pc.group(1).replace(" ", "") if pc else None,
            "town": town.group(1).strip() if town else None,
            "labelled": bool(re.search(r"(property|address)\s*:?\s*$", text[max(0, m.start() - 12):m.start()], re.I)),
        })
    return out


def focus_floor(text: str) -> str | None:
    m = re.search(rf"(?:to\s+let|for\s+sale|available)\W{{1,4}}{FLOOR_RE}", text[:400], re.I)
    return floor_slug(m.group(1)) if m else None


def classify(doc: Document, registry: dict[str, str]) -> dict:
    text = _all_text(doc)
    doc_type, scores = guess_doc_type(text)
    issuer, role = find_issuer(doc, text, doc_type)
    dates = find_dates(doc, text, doc_type)
    statuses = [p.text_status for p in doc.pages]
    meta = doc.metadata or {}
    synthetic = "synthetic: true" in (meta.get("subject", "") + meta.get("keywords", ""))
    return {
        "doc_id": make_doc_id(doc.path, doc.sha256, registry),
        "file_uri": doc.path,
        "sha256": doc.sha256,
        "page_count": doc.page_count,
        "doc_type": doc_type,
        "doc_type_scores": scores,
        "authority_tier": DOC_TYPE_TIER.get(doc_type),
        "issuer_org": issuer,
        "issuer_role": role,
        **dates,
        "has_text_layer": any(s in ("good", "partial_garbled") for s in statuses),
        "text_layer": {"pages": statuses, "garbled_pages": [p.page_no for p in doc.pages if p.garbled_ratio > 0.02]},
        "source": "synthetic" if synthetic else "real",
        "focus_floor": focus_floor(text),
        "_development_wide": bool(re.search(r"all\s+house\s+types|standard\s+specification\s+for\s+the\s+development", text, re.I)),
        "_addresses": address_candidates(text),
    }


# ---------------------------------------------------------------- entity resolution

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def resolve_entities(docs: list[dict], bedrooms_by_doc: dict[str, int | None]) -> None:
    """Assign development_id and the document's subject unit_id. Never merges unnumbered houses."""
    df = Counter()
    for d in docs:
        for name in {a["name"] for a in d["_addresses"]}:
            df[name] += 1
    clusters: dict[str, list[tuple[dict, dict]]] = {}
    for d in docs:
        cands = d["_addresses"]
        if not cands:
            d["development_id"] = None
            d["unit_id"] = None
            continue
        counts = Counter(a["name"] for a in cands)

        def score(a):
            return (df[a["name"]] + (0.5 if re.search(BUILDING_SUFFIX, a["name"]) else 0) + (1 if a["labelled"] else 0)
                    + 0.01 * counts[a["name"]])
        best = max(cands, key=score)
        clusters.setdefault(best["name"], []).append((d, best))

    for name, members in clusters.items():
        postcodes = Counter(a["postcode"] for d, _ in members for a in d["_addresses"] if a["name"] == name and a["postcode"])
        towns = Counter(_slug(a["town"]) for d, _ in members for a in d["_addresses"] if a["name"] == name and a["town"])
        qual = postcodes.most_common(1)[0][0] if postcodes else (towns.most_common(1)[0][0] if towns else "")
        dev_id = _slug(f"{name} {qual}")
        is_building = bool(re.search(BUILDING_SUFFIX, name))
        for d, _ in members:
            d["development_id"] = dev_id
            d["development_name"] = name
            numbers = Counter(a["number"] for a in d["_addresses"] if a["name"] == name and a["number"])
            if d["_development_wide"]:
                d["unit_id"], d["entity_match_status"] = f"{dev_id}:development", "matched"
            elif is_building:
                d["unit_id"], d["entity_match_status"] = f"{dev_id}:whole", "matched"
            elif numbers:
                d["unit_id"], d["entity_match_status"] = f"{dev_id}:no-{numbers.most_common(1)[0][0]}", "matched"
            else:
                beds = bedrooms_by_doc.get(d["doc_id"])
                d["unit_id"] = f"{dev_id}:{beds}-bed-unnumbered" if beds else f"{dev_id}:unnumbered-{d['doc_id']}"
                d["entity_match_status"] = "ambiguous"
