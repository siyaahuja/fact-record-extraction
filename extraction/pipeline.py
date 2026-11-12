"""End to end: folder of PDFs -> documents.jsonl, facts.jsonl, rejected.jsonl, summary, contradictions."""
from __future__ import annotations

import glob
import json
import os
import sys
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import classify as cls
from . import rules
from .contradictions import detect
from .llm import get_provider, llm_extract_page
from .pdfio import load_document
from .validate import validate

CONTRACT_KEYS = ("doc_id", "unit_hint", "scope", "field", "qualifier", "value_raw", "value", "normalised",
                 "page", "quote", "doc_error", "confidence")
EXTRA_KEYS = ("fact_id", "development_id", "unit_id", "as_at", "authority_tier", "extraction_method",
              "quote_source", "quote_match", "unit_check", "status")


def _load_registry(folder: str) -> dict[str, str]:
    """Optional doc_id registry: an ingest manifest listing files by sha256. Only doc_id is taken from it."""
    path = os.path.join(folder, "manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        m = json.load(f)
    return {d["sha256"]: d["doc_id"] for d in m.get("documents", []) if d.get("sha256") and d.get("doc_id")}


def _dedupe_key(f: dict) -> tuple:
    v = f["value"]
    if f["field"] == "floor_area":
        core = round(f["normalised"]["sq_m"])
    else:
        core = json.dumps({k: v[k] for k in sorted(v) if k not in ("text", "kind", "score", "certificate_date")}, sort_keys=True)
    return (f["doc_id"], f["page"], f["field"], json.dumps(f["qualifier"], sort_keys=True), core)


def _rank(f: dict) -> tuple:
    method = 0 if f["extraction_method"].startswith("llm") else 1
    src = {"pdf_text_table": 0, "pdf_text": 1, "ocr_table": 2, "layout_rows": 2, "ocr": 3, "repaired_text": 4}.get(f.get("text_source", ""), 5)
    return (method, f.get("doc_error") is False, src, -len(f.get("value", {})), len(f["quote"]))


def _assign_unit(f: dict, doc: dict) -> None:
    dev, base = doc.get("development_id"), doc.get("unit_id")
    q = f["qualifier"]
    scope_q = q.get("scope") if f["field"] in ("floor_area", "availability") else None
    floor = f.pop("unit_floor", None)
    if scope_q and scope_q.startswith("floor:"):
        floor = scope_q.split(":", 1)[1]
    if f["field"] == "rent" and not floor and q.get("per") == "floor" and doc.get("focus_floor"):
        floor = doc["focus_floor"]
    if floor and not (base or "").endswith(":whole"):
        floor = None
    if dev and floor:
        f["unit_id"], f["unit_hint"], f["scope"] = f"{dev}:{floor.replace('_', '-')}", f"{floor.replace('_', ' ')} floor", "unit"
    elif dev and scope_q and scope_q.startswith("house_type:"):
        t = scope_q.split(":", 1)[1].lower()
        f["unit_id"], f["unit_hint"], f["scope"] = f"{dev}:type-{t}", f"house type {t.upper()}", "house_type"
    elif dev and scope_q and scope_q.startswith("plot:"):
        p = scope_q.split(":", 1)[1].lower()
        f["unit_id"], f["unit_hint"], f["scope"] = f"{dev}:no-{p}", f"plot {p}", "plot"
    else:
        f["unit_id"] = base
        if base and base.endswith(":development"):
            f["scope"], f["unit_hint"] = "development", "development-wide"
        elif base and base.endswith(":whole"):
            f["scope"] = f.get("scope") or "building"
            f["unit_hint"] = "whole building"
        else:
            f["scope"] = f.get("scope") or "unit"
            f["unit_hint"] = base.split(":", 1)[1] if base else None
    f["development_id"] = dev


def _order(f: dict) -> dict:
    out = {k: f.get(k) for k in CONTRACT_KEYS}
    out.update({k: f.get(k) for k in EXTRA_KEYS if f.get(k) is not None})
    return out


def run(input_dir: str, out_dir: str, extractor: str = "auto", cache_dir: str = ".cache", workers: int = 4,
        log=print) -> dict:
    files = sorted(glob.glob(os.path.join(input_dir, "**", "*.pdf"), recursive=True))
    if not files:
        raise SystemExit(f"no PDFs under {input_dir}")
    provider = None
    if extractor in ("auto", "llm", "hybrid"):
        provider = get_provider(cache_dir=cache_dir)
        if provider is None:
            if extractor != "auto":
                raise SystemExit("LLM extractor requested but no API key found. Set ANTHROPIC_API_KEY, "
                                 "OPENAI_API_KEY or XAI_API_KEY (see README).")
            log("! no LLM API key found (ANTHROPIC_API_KEY / OPENAI_API_KEY / XAI_API_KEY): "
                "running the deterministic rules extractor only")
            extractor = "rules"
        elif extractor == "auto":
            extractor = "hybrid"
    log(f"extractor: {extractor}" + (f" ({provider.name}:{provider.model})" if provider else ""))

    registry = _load_registry(input_dir)
    loaded, docs = [], []
    with ThreadPoolExecutor(workers) as ex:
        loaded = list(ex.map(lambda p: load_document(p, cache_dir=cache_dir), files))
    for d in loaded:
        docs.append(cls.classify(d, registry))
        log(f"  loaded {docs[-1]['doc_id']:<24} {d.page_count}p text={docs[-1]['text_layer']['pages']}")

    candidates: dict[str, list[dict]] = {}
    for d, meta in zip(loaded, docs):
        cands = []
        for page in d.pages:
            if extractor in ("rules", "hybrid"):
                cands += rules.extract_page(page, meta["doc_type"], meta["focus_floor"])
        candidates[meta["doc_id"]] = cands

    if extractor in ("llm", "hybrid"):
        jobs = [(d, meta, page) for d, meta in zip(loaded, docs) for page in d.pages]

        def work(job):
            d, meta, page = job
            try:
                return meta["doc_id"], llm_extract_page(provider, page, meta), None
            except Exception as e:  # keep going; the page is reported as failed
                return meta["doc_id"], [], f"p{page.page_no}: {type(e).__name__}: {e}"
        with ThreadPoolExecutor(workers) as ex:
            for doc_id, cands, err in ex.map(work, jobs):
                candidates[doc_id] += cands
                if err:
                    log(f"  ! LLM failed on {doc_id} {err}")
                    next(m for m in docs if m["doc_id"] == doc_id).setdefault("llm_errors", []).append(err)

    beds = {}
    for meta in docs:
        b = Counter(c["value"].get("count") for c in candidates[meta["doc_id"]] if c["field"] == "bedrooms")
        beds[meta["doc_id"]] = b.most_common(1)[0][0] if b else None
    cls.resolve_entities(docs, beds)

    facts, rejected = [], []
    for d, meta in zip(loaded, docs):
        pages = {p.page_no: p for p in d.pages}
        hay: dict = {}
        best: dict[tuple, dict] = {}
        for c in candidates[meta["doc_id"]]:
            c["doc_id"] = meta["doc_id"]
            ok, reason = validate(dict(c), pages, hay)
            if ok is None:
                rejected.append({**{k: c.get(k) for k in ("doc_id", "page", "field", "value_raw", "quote", "extraction_method")},
                                 "reason": reason})
                continue
            key = _dedupe_key(ok)
            if key not in best or _rank(ok) < _rank(best[key]):
                best[key] = ok
        for f in best.values():
            _assign_unit(f, meta)
            f["fact_id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(_dedupe_key(f)) + f["quote"]))
            f["as_at"] = meta.get("register_date") if meta["authority_tier"] == 2 and meta.get("register_date") else meta.get("doc_date")
            f["authority_tier"] = meta["authority_tier"]
            f["status"] = "extracted"
            facts.append(f)
    facts.sort(key=lambda f: (f["doc_id"], f["page"], f["field"]))

    contradictions = detect(facts, docs)
    os.makedirs(out_dir, exist_ok=True)
    public_docs = [{k: v for k, v in m.items() if not k.startswith("_")} for m in docs]
    _write_jsonl(os.path.join(out_dir, "documents.jsonl"), public_docs)
    _write_jsonl(os.path.join(out_dir, "facts.jsonl"), [_order(f) for f in facts])
    _write_jsonl(os.path.join(out_dir, "rejected.jsonl"), rejected)
    _write_jsonl(os.path.join(out_dir, "contradictions.jsonl"), contradictions)
    summary = write_summary(out_dir, public_docs, facts, rejected, contradictions, extractor)
    log(f"wrote {len(facts)} facts, {len(rejected)} rejected candidates, {len(contradictions)} contradictions -> {out_dir}/")
    return summary


def _write_jsonl(path: str, rows: list[dict]) -> None:
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _fmt_value(f: dict) -> str:
    v = f["value"]
    if f["field"] in ("price", "rent"):
        return f"£{v['amount']:,.0f}"
    if f["field"] == "floor_area":
        n = f["normalised"]
        return f"{n['sq_ft']:,} sq ft / {n['sq_m']:,} sq m" + (" DOC_ERROR" if f["doc_error"] else "")
    return ", ".join(f"{k}={v[k]}" for k in v if k != "text")


def write_summary(out_dir, docs, facts, rejected, contradictions, extractor) -> dict:
    by_doc = defaultdict(list)
    for f in facts:
        by_doc[f["doc_id"]].append(f)
    rej = Counter(r["doc_id"] for r in rejected)
    lines = [f"# Extraction summary (extractor: {extractor})", ""]
    summary = {"extractor": extractor, "documents": []}
    for d in docs:
        fs = by_doc[d["doc_id"]]
        s = {"doc_id": d["doc_id"], "doc_type": d["doc_type"], "tier": d["authority_tier"], "issuer": d["issuer_org"],
             "doc_date": d["doc_date"], "doc_date_source": d["doc_date_source"], "pages": d["page_count"],
             "text_layer": d["text_layer"]["pages"], "unit_id": d.get("unit_id"),
             "facts": len(fs), "fields": dict(Counter(f["field"] for f in fs)), "doc_errors": sum(f["doc_error"] for f in fs),
             "rejected": rej[d["doc_id"]]}
        summary["documents"].append(s)
        lines += [f"## {d['doc_id']} ({d['doc_type']}, tier {d['authority_tier']}, {d['issuer_org']}, {d['doc_date']} [{d['doc_date_source']}])",
                  f"{d['page_count']} pages, text layer {d['text_layer']['pages']}, unit `{d.get('unit_id')}`, "
                  f"{len(fs)} facts, {rej[d['doc_id']]} rejected candidates", ""]
        for f in fs:
            lines.append(f"- p{f['page']} **{f['field']}** {json.dumps(f['qualifier'])} = {_fmt_value(f)}  "
                         f"[{f['unit_id']}] \"{f['quote'][:90]}\"")
        lines.append("")
    lines += ["## Contradictions", ""]
    for c in contradictions:
        lines.append(f"- {c['type']} | {c['unit_id']} | {c['field']} {c['qualifier_key']} | {c['rule_applied']} | "
                     f"{', '.join(c['values'])}")
    with open(os.path.join(out_dir, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
