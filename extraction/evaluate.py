"""Score an extraction run (out/) against three answer keys and print pass/fail tables.

1. Documents vs sample_data/manifest.json: doc_type, tier, issuer, pages, text layer, date, unit.
2. Facts vs eval/golden_real.json (hand-written for the real brochures) and vs every evidence item in
   sample_data/contradictions.json (parsed generically from its value text, so a new answer key just works).
3. Contradictions vs contradictions.json: was a contradiction of the expected type found over the evidence docs?
Entries whose documents aren't in the run are skipped, not failed.
"""
from __future__ import annotations

import json
import os
import re

from .units import AREA_UNIT, NUM, WORD_NUMBERS, area_unit, normalise_area, parse_number

FIELD_ALIASES = {"en_suite_fittings": ["bathroom_fixture"], "bedrooms": ["bedrooms"]}
CORE = ("price", "rent", "tenure", "transaction_type", "floor_area", "epc_rating", "parking")


def _load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def _close(a, b, rel=0.005, abs_=0.6):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))
    return a == b


def _matches(f: dict, exp: dict) -> bool:
    if f["doc_id"] != exp["doc_id"] or f["field"] != exp["field"]:
        return False
    if exp.get("page") and f["page"] != exp["page"]:
        return False
    for k, v in (exp.get("qualifier") or {}).items():
        if f["qualifier"].get(k) != v:
            return False
    if exp.get("type_any") and f["qualifier"].get("type") not in exp["type_any"]:
        return False
    for k, v in (exp.get("value") or {}).items():
        if not _close(f["value"].get(k), v):
            return False
    for k, v in (exp.get("normalised") or {}).items():
        if not f.get("normalised") or not _close(f["normalised"].get(k), v, rel=0.01, abs_=1.0):
            return False
    if "doc_error" in exp and bool(f.get("doc_error")) != exp["doc_error"]:
        return False
    return True


def _describe(exp: dict) -> str:
    parts = [exp["field"]]
    if exp.get("qualifier"):
        parts.append(",".join(f"{k}={v}" for k, v in exp["qualifier"].items()))
    if exp.get("value"):
        parts.append(",".join(f"{k}={v}" for k, v in exp["value"].items()))
    if exp.get("normalised"):
        parts.append(",".join(f"{k}~{v}" for k, v in exp["normalised"].items()))
    if "doc_error" in exp:
        parts.append(f"doc_error={exp['doc_error']}")
    if exp.get("absent"):
        parts.append("ABSENT")
    return " ".join(parts)


def _closest(facts, exp):
    cands = [f for f in facts if f["doc_id"] == exp["doc_id"] and f["field"] == exp["field"]]
    if not cands:
        return "no fact of this field"
    f = cands[0]
    return f"got p{f['page']} {json.dumps(f['qualifier'])} {json.dumps(f['value'])}" + (" doc_error" if f.get("doc_error") else "")


def _table(title, header, rows):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    widths = [min(w, 70) for w in widths]
    print(f"\n{title}")
    line = "  ".join(str(h).ljust(w) for h, w in zip(header, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(c)[:70].ljust(w) for c, w in zip(r, widths)))


# ------------------------------------------------------------------ documents vs manifest

def eval_documents(docs, manifest):
    rows, passed, total = [], 0, 0
    by_id = {d["doc_id"]: d for d in docs}
    for m in manifest.get("documents", []):
        d = by_id.get(m["doc_id"])
        if d is None:
            continue
        exp_src = (m.get("date_source") or "").split(" ")[0]
        checks = {
            "doc_type": d["doc_type"] == m.get("doc_type"),
            "tier": d["authority_tier"] == m.get("authority_tier"),
            "issuer": bool(d.get("issuer_org")) and _norm_org(d["issuer_org"]) in _norm_org(m.get("issuer", "")) or
                      _norm_org(m.get("issuer", "").split("(")[0]) in _norm_org(d.get("issuer_org") or "-"),
            "pages": d["page_count"] == m.get("page_count"),
            "text_layer": d["has_text_layer"] == m.get("has_text_layer"),
            "date": bool(d.get("doc_date")) and str(d["doc_date"])[:7] == str(m.get("date"))[:7],
            "printed?": (d.get("doc_date_source") or "").startswith("printed") == exp_src.startswith("printed"),
            "unit": bool(d.get("unit_id")) and str(m.get("unit", "")).startswith(d["unit_id"]),
        }
        ok = sum(checks.values())
        passed += ok
        total += len(checks)
        rows.append([m["doc_id"]] + ["ok" if v else "FAIL" for v in checks.values()] +
                    [f"{d['doc_type']}/{d['issuer_org']}/{d['doc_date']}[{d['doc_date_source']}]/{d.get('unit_id')}"])
    if rows:
        _table("DOCUMENTS vs manifest.json", ["doc_id", "type", "tier", "issuer", "pages", "text", "date", "printed?", "unit", "extracted"], rows)
        print(f"documents: {passed}/{total} checks pass")
    return passed, total


def _norm_org(s: str) -> str:
    s = re.sub(r"\(.*?\)", "", s or "").lower()
    s = re.sub(r"\b(ltd|limited|llp|plc|chartered|surveyors)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


# ------------------------------------------------------------------ facts vs golden

def eval_golden(facts, golden, doc_ids):
    rows, passed, total = [], 0, 0
    for exp in golden.get("facts", []):
        if exp["doc_id"] not in doc_ids:
            continue
        hits = [f for f in facts if _matches(f, exp)]
        ok = (not hits) if exp.get("absent") else bool(hits)
        passed += ok
        total += 1
        detail = (f"p{hits[0]['page']} \"{hits[0]['quote'][:50]}\"" if hits and not exp.get("absent")
                  else ("found: " + hits[0]["quote"][:50]) if hits else ("" if exp.get("absent") else _closest(facts, exp)))
        rows.append([exp["id"], exp["doc_id"], _describe(exp), "PASS" if ok else "FAIL", detail])
    if rows:
        _table("CORE FACTS vs eval/golden_real.json", ["id", "doc_id", "expected", "result", "evidence / closest"], rows)
        print(f"golden facts: {passed}/{total} pass")
    return passed, total, rows


# ------------------------------------------------------------------ facts vs contradictions.json evidence

def _parse_evidence(field: str, qualifier: dict, text: str) -> list[dict]:
    """Turn an answer-key value string into one or more expected value checks."""
    t = text.lower()
    if field in ("price", "rent"):
        m = re.search(rf"£\s?({NUM})", text)
        return [{"value": {"amount": float(m.group(1).replace(',', ''))}}] if m else []
    if field == "epc_rating":
        m = re.search(r"\b([A-G])\b", text)
        return [{"value": {"band": m.group(1)}}] if m else []
    if field == "parking":
        m = re.search(rf"\b(\d+|{'|'.join(WORD_NUMBERS)})\b", t)
        n = parse_number(m.group(1)) if m else None
        return [{"value": {"spaces": int(n)}}] if n else []
    if field == "floor_area":
        out = []
        for part in text.split(";"):
            m = re.search(rf"({NUM})\s*({AREA_UNIT})", part, re.I)
            if not m:
                continue
            unit = area_unit(m.group(2))
            norm = normalise_area(float(m.group(1).replace(",", "")), unit)
            basis = ("NIA" if re.search(r"\bnia\b|\bnet\b", part, re.I) else "GIA" if re.search(r"\bgia\b|gross", part, re.I)
                     else "EPC" if re.search(r"\bepc\b", part, re.I) else None)
            q = {}
            if basis:
                q["basis"] = basis
            out.append({"normalised": {"sq_m": norm["sq_m"]}, "qualifier": q})
        return out
    return [{}]


def eval_evidence(facts, key, doc_ids):
    rows, passed, total = [], 0, 0
    for c in key.get("contradictions", []):
        fields = FIELD_ALIASES.get(c["field"], None)
        if fields is None:
            fields = [x.strip() for x in c["field"].split("/")]
            fields = [g for f in fields for g in FIELD_ALIASES.get(f, [f])]
        for e in c["evidence"]:
            if e["doc_id"] not in doc_ids:
                continue
            checks = []
            for fld in fields:
                for chk in _parse_evidence(fld, c.get("qualifier") or {}, e["value"]):
                    checks.append({"doc_id": e["doc_id"], "page": e["page"], "field": fld, **chk})
            ok = any(any(_matches(f, chk) for f in facts) for chk in checks) if checks else False
            passed += ok
            total += 1
            rows.append([c["id"], e["doc_id"], e["page"], c["field"], e["value"][:45], "PASS" if ok else "FAIL"])
    if rows:
        _table("FACTS vs contradictions.json evidence (value found on the cited doc and page)",
               ["id", "doc_id", "page", "field", "expected value", "result"], rows)
        print(f"evidence facts: {passed}/{total} pass")
    return passed, total


# ------------------------------------------------------------------ contradictions

def eval_contradictions(found, key, doc_ids):
    rows, passed, total = [], 0, 0
    for c in key.get("contradictions", []):
        ev_docs = {e["doc_id"] for e in c["evidence"]}
        if not ev_docs <= doc_ids:
            continue
        fields = set(FIELD_ALIASES.get(c["field"], [])) or {g for f in c["field"].split("/") for g in FIELD_ALIASES.get(f.strip(), [f.strip()])}
        dev = c["unit"].split(":")[0]
        same_field = [x for x in found if x["field"] in fields and x["unit_id"].startswith(dev)]
        overlap = [x for x in same_field if len(ev_docs & set(x["doc_ids"])) >= min(2, len(ev_docs))]
        typed = [x for x in overlap if x["type"] == c["type"]]
        ok = bool(typed)
        passed += ok
        total += 1
        got = typed[0] if typed else (overlap[0] if overlap else None)
        rows.append([c["id"], c["field"][:18], c["type"], "PASS" if ok else "FAIL",
                     (f"{got['type']} {got['unit_id'].split(':', 1)[-1][:30]} {got['rule_applied']}" if got else "not detected")])
    if rows:
        _table("CONTRADICTIONS vs contradictions.json", ["id", "field", "expected type", "result", "detected"], rows)
        print(f"contradictions: {passed}/{total} detected with the expected type")
    return passed, total


def main(out_dir="out", input_dir="sample_data", golden_path="eval/golden_real.json", manifest_path=None, key_path=None) -> int:
    manifest_path = manifest_path or os.path.join(input_dir, "manifest.json")
    key_path = key_path or os.path.join(input_dir, "contradictions.json")
    facts = _load_jsonl(os.path.join(out_dir, "facts.jsonl"))
    docs = _load_jsonl(os.path.join(out_dir, "documents.jsonl"))
    found = _load_jsonl(os.path.join(out_dir, "contradictions.jsonl"))
    doc_ids = {d["doc_id"] for d in docs}
    results = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            results["documents"] = eval_documents(docs, json.load(f))
    golden_rows = []
    if os.path.exists(golden_path):
        with open(golden_path) as f:
            p, t, golden_rows = eval_golden(facts, json.load(f), doc_ids)
            results["golden"] = (p, t)
    if os.path.exists(key_path):
        with open(key_path) as f:
            key = json.load(f)
        results["evidence"] = eval_evidence(facts, key, doc_ids)
        results["contradictions"] = eval_contradictions(found, key, doc_ids)

    print("\nSUMMARY")
    for name, (p, t) in results.items():
        print(f"  {name:<15} {p:>3}/{t:<3} {'PASS' if p == t else 'partial'}")
    kelso = [r for r in golden_rows if r[1].startswith("carterjonas")]
    if kelso:
        ok = all(r[3] == "PASS" for r in kelso)
        print(f"  kelso core fields (both real brochures, incl. 185/2,700 doc_error): {'PASS' if ok else 'FAIL'}")
    with open(os.path.join(out_dir, "eval.json"), "w") as f:
        json.dump({k: {"passed": p, "total": t} for k, (p, t) in results.items()}, f, indent=2)
    return 0
