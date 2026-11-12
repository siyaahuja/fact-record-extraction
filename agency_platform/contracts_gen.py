"""Per-development contracts 01-05 produced by contracts/build.py (the source of truth), plus UI views over them.

build.py works on one global out/ dir and a fixed development list; here it is pointed at one development's
extractor output at a time. 02 is append-only; `unreject_fact` and `reopen_contradiction` are platform actions
that cancel earlier actions on the same id before build.py applies the rest.
"""
from __future__ import annotations

import importlib.util
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("contracts_build", ROOT / "contracts" / "build.py")
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)
_LOCK = threading.Lock()

TYPE_PLAIN = {
    "version_supersession": "A newer version of the same document says something different",
    "true_conflict": "Two equally authoritative sources disagree",
    "unit_or_measurement_mismatch": "Same area quoted in different units or on a different basis",
    "scope_difference": "One source talks about the whole development, the other about this home",
    "plot_or_type_variation": "The figures belong to a different plot or house type",
    "stale_listing": "A portal listing is out of date versus a newer document",
    "official_record_mismatch": "A document disagrees with the official register",
}
FIELD_LABEL = {
    "price": "Price", "rent": "Rent", "tenure": "Tenure", "transaction_type": "Transaction", "floor_area": "Floor area",
    "epc_rating": "EPC rating", "parking": "Parking", "bedrooms": "Bedrooms", "bathrooms": "Bathrooms",
    "bathroom_fixture": "Bathroom fittings", "availability": "Availability", "listed_status": "Listed status",
}
TIER_LABEL = {1: "Legal instrument", 2: "Official register", 3: "Measured / signed spec", 4: "Developer instruction",
              5: "Agent particulars", 6: "Portal / CRM"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def contract_name(dev_id: str, slug: str) -> str:
    return next((n for d, n in cb.DEVELOPMENTS.items() if d == dev_id), slug)


def build_all(slug: str, dev_id: str, primary_unit: str | None, out_dir: Path, work_dir: Path, actions: dict | None) -> dict:
    """Returns {"01": ..., "02": ..., "03": ..., "04": ..., "05": ...} for one development."""
    name = contract_name(dev_id, slug)
    key = json.loads((ROOT / "sample_data" / "contradictions.json").read_text())
    key["contradictions"] = [c for c in key["contradictions"] if c["development"] == dev_id]
    key_path = work_dir / "contradictions_key.json"
    key_path.write_text(json.dumps(key))
    with _LOCK:
        saved = (cb.OUT, cb.KEY, cb.DEVELOPMENTS, cb.LISTING_UNITS)
        try:
            cb.OUT, cb.KEY = str(out_dir), str(key_path)
            cb.DEVELOPMENTS = {dev_id: name}
            cb.LISTING_UNITS = {name: primary_unit} if primary_unit else {}
            extracted = cb.build_extracted()
            seeded = cb.seed_review(extracted)
            if actions is None:
                actions = {**seeded, "actions": []}
            actions["shapes"] = {**seeded["shapes"],
                                 "unreject_fact": {"action": "unreject_fact", "fact_id": "<fact id>", "reviewer": {}, "at": "ISO-8601 UTC"},
                                 "reopen_contradiction": {"action": "reopen_contradiction", "contradiction_id": "C01..", "reviewer": {}, "at": "ISO-8601 UTC"}}
            resolved = cb.apply_review(extracted, effective(actions))
            voice = cb.voice_agent(resolved)
            listing = cb.listing(resolved)
        finally:
            cb.OUT, cb.KEY, cb.DEVELOPMENTS, cb.LISTING_UNITS = saved
    return {"01": extracted, "02": actions, "03": resolved, "04": voice, "05": listing}


def effective(review: dict) -> dict:
    out = []
    for a in review["actions"]:
        if a["action"] == "unreject_fact":
            out = [x for x in out if not (x["action"] == "reject_fact" and x.get("fact_id") == a["fact_id"])]
        elif a["action"] == "reopen_contradiction":
            out = [x for x in out if not (x["action"] == "resolve_contradiction" and x.get("contradiction_id") == a["contradiction_id"])]
        else:
            out.append(a)
    return {**review, "actions": out}


def dev_of(contract: dict) -> dict:
    return next(iter(contract["developments"].values()), {"facts": [], "contradictions": [], "documents": []})


def ui_facts(resolved: dict, raw_facts: dict) -> list[dict]:
    dev = dev_of(resolved)
    open_by_fact: dict[str, list[str]] = {}
    for c in dev["contradictions"]:
        if c["status"] == "open":
            for fid in c["fact_ids"]:
                open_by_fact.setdefault(fid, []).append(c["id"])
    out = []
    for f in dev["facts"]:
        raw = raw_facts.get(f["id"], {})
        status = "pending" if f["status"] == "accepted" else f["status"]
        out.append({**f, "fact_id": f["id"], "display_value": f["display"], "status": status,
                    "review_status": "rejected" if f["status"] == "rejected" else "accepted",
                    "open_contradictions": sorted(set(open_by_fact.get(f["id"], []))),
                    "scope": raw.get("scope", f.get("scope")), "quote_source": raw.get("quote_source"),
                    "quote_match": raw.get("quote_match"), "as_at": raw.get("as_at", f.get("doc_date"))})
    return out


def ui_contradictions(resolved: dict, facts: list[dict]) -> list[dict]:
    dev = dev_of(resolved)
    by_id = {f["fact_id"]: f for f in facts}
    out = []
    for c in dev["contradictions"]:
        cands = []
        for fid in c["fact_ids"]:
            f = by_id.get(fid)
            if f:
                cands.append({"fact_id": fid, "value": f["display"], "unit_id": f["unit_id"], "scope": f.get("scope"),
                              "doc_error": f.get("doc_error"), "doc_id": f["doc_id"], "page": f["page"], "quote": f["quote"],
                              "issuer": f.get("issuer"), "authority_tier": f.get("authority_tier"), "as_at": f.get("as_at"),
                              "tier_label": TIER_LABEL.get(f.get("authority_tier"))})
        cands.sort(key=lambda x: (x["authority_tier"] or 9, "".join(chr(255 - ord(ch)) for ch in str(x["as_at"] or ""))))
        rec = c.get("recommended_fact_id")
        res = c.get("resolution") or {}
        out.append({**c, "contradiction_id": c["id"], "label": c["id"],
                    "field_label": FIELD_LABEL.get(c["field"], c["field"]), "type_plain": TYPE_PLAIN.get(c["type"], c["type"]),
                    "candidates": cands,
                    "recommended": {"fact_id": rec, "value": by_id[rec]["display"] if rec in by_id else None,
                                    "reason": c.get("recommendation_reason")},
                    "resolution": res.get("kind"), "resolved_fact_id": res.get("winning_fact_id"),
                    "resolved_by": (res.get("reviewer") or {}).get("name") or (res.get("reviewer") or {}).get("id"),
                    "resolved_at": res.get("at")})
    return out
