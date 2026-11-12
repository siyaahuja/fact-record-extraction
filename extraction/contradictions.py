"""Light contradiction detection over extracted facts, following the schema's classification order.

Pairs of facts from different documents about the same unit and field are compared; disagreeing pairs
are classified (scope, entity, unit/basis, official record, stale listing, version, true conflict)
and merged into one contradiction per (unit, field, comparison key, type).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from itertools import combinations

from .catalogue import MATERIAL_FIELDS

AREA_TOLERANCE = 0.005
COMPARED_FIELDS = ("price", "rent", "tenure", "transaction_type", "floor_area", "epc_rating", "parking",
                   "bedrooms", "bathrooms", "bathroom_fixture", "availability", "listed_status")
AGENT_STATE = {
    "true_conflict": "do_not_quote_conflicting", "official_record_mismatch": "do_not_quote_conflicting",
    "version_supersession": "do_not_quote_pending", "stale_listing": "quote_verified",
    "unit_or_measurement_mismatch": "quote_with_scope", "scope_difference": "quote_with_scope",
    "plot_or_type_variation": "quote_with_scope",
}


def _value_key(f: dict):
    v = f["value"]
    if f["field"] == "floor_area":
        return round(f["normalised"]["sq_m"], 1)
    if f["field"] in ("price", "rent"):
        return v.get("amount")
    if f["field"] == "epc_rating":
        return v.get("band")
    if f["field"] == "parking":
        return v.get("spaces")
    return json.dumps({k: v[k] for k in sorted(v) if k != "text"}, sort_keys=True)


def _differ(a: dict, b: dict) -> bool:
    if a["field"] == "floor_area":
        x, y = a["normalised"]["sq_m"], b["normalised"]["sq_m"]
        return abs(x - y) / max(x, y) > AREA_TOLERANCE or a["doc_error"] or b["doc_error"]
    return _value_key(a) != _value_key(b)


def _display(f: dict) -> str:
    v = f["value"]
    if f["field"] in ("price", "rent"):
        s = f"£{v['amount']:,.0f}"
    elif f["field"] == "floor_area":
        s = f"{f['value_raw']} {f['qualifier'].get('basis')}" + (" (doc_error)" if f["doc_error"] else "")
    else:
        s = str(_value_key(f))
    return f"{s} [{f['doc_id']} p{f['page']}]"


def _classify_pair(a: dict, b: dict, docs: dict) -> tuple[str, dict | None, str]:
    da, db = docs[a["doc_id"]], docs[b["doc_id"]]
    qa, qb = a["qualifier"], b["qualifier"]
    if a["field"] == "parking" and qa.get("scope") != qb.get("scope"):
        return "scope_difference", None, "keep_both_scoped"
    if a["field"] == "floor_area" and (qa.get("basis") != qb.get("basis") or a["doc_error"] or b["doc_error"]):
        good = [f for f in (a, b) if not f["doc_error"] and f["qualifier"].get("basis") != "unspecified"]
        return "unit_or_measurement_mismatch", (good[0] if len(good) == 1 else None), "normalise_and_label"
    ta, tb = a["authority_tier"] or 9, b["authority_tier"] or 9
    oa, ob = ta == 2 or bool(a.get("cites_official_record")), tb == 2 or bool(b.get("cites_official_record"))
    if oa != ob:
        return "official_record_mismatch", (a if oa else b), "human_required"
    newer = a if (da.get("doc_date") or "") > (db.get("doc_date") or "") else b
    if 6 in (ta, tb) and ta != tb:
        other = b if ta == 6 else a
        if (docs[other["doc_id"]].get("doc_date") or "") >= (docs[(a if ta == 6 else b)["doc_id"]].get("doc_date") or "") or other is newer:
            return "stale_listing", other, "latest_document_wins"
    if da.get("issuer_org") == db.get("issuer_org") and da.get("doc_type") == db.get("doc_type") and da.get("doc_date") != db.get("doc_date"):
        return "version_supersession", newer, "same_issuer_later_supersedes"
    if ta != tb:
        higher = a if ta < tb else b
        if higher is newer:
            return "version_supersession", higher, "later_higher_tier_supersedes"
        return "true_conflict", higher, "higher_tier_candidate_human_required"
    return "true_conflict", None, "human_required"


def _group_key(f: dict) -> tuple:
    q = f["qualifier"]
    if f["field"] == "floor_area":
        return (f["unit_id"], f["field"], f"scope={q.get('scope')}")
    if f["field"] in ("price", "parking", "availability", "transaction_type"):
        return (f["unit_id"], f["field"], "")
    return (f["unit_id"], f["field"], json.dumps(q, sort_keys=True))


def detect(facts: list[dict], docs_list: list[dict]) -> list[dict]:
    docs = {d["doc_id"]: d for d in docs_list}
    units = {d.get("unit_id"): d.get("entity_match_status") for d in docs_list}
    groups = defaultdict(list)
    for f in facts:
        if f["field"] in COMPARED_FIELDS and f.get("unit_id"):
            groups[_group_key(f)].append(f)

    merged: dict[tuple, dict] = {}

    def add(key, type_, a, b, candidate, rule):
        k = key + (type_,)
        c = merged.setdefault(k, {"unit_id": key[0], "field": key[1], "qualifier_key": key[2], "type": type_,
                                  "facts": {}, "candidates": [], "rule_applied": rule})
        c["facts"][a["fact_id"]] = a
        c["facts"][b["fact_id"]] = b
        if candidate is not None:
            c["candidates"].append(candidate)

    for key, fs in groups.items():
        for a, b in combinations(fs, 2):
            if a["doc_id"] == b["doc_id"] and not (a["doc_error"] or b["doc_error"]):
                continue
            if not _differ(a, b):
                continue
            t, cand, rule = _classify_pair(a, b, docs)
            add(key, t, a, b, cand, rule)

    by_dev_field = defaultdict(list)
    for f in facts:
        if f["field"] in COMPARED_FIELDS and f.get("development_id"):
            by_dev_field[(f["development_id"], f["field"])].append(f)
    for (dev, field), fs in by_dev_field.items():
        for a, b in combinations(fs, 2):
            if a["unit_id"] == b["unit_id"] or not _differ(a, b):
                continue
            ua, ub = a["unit_id"], b["unit_id"]
            if ua.endswith(":development") != ub.endswith(":development"):
                unit = ub if ua.endswith(":development") else ua
                add((f"{unit} vs {dev}:development", field, "scope=development_vs_unit"), "scope_difference", a, b, None, "keep_both_scoped")
            elif (":type-" in ua) != (":type-" in ub) and json.dumps(a["qualifier"], sort_keys=True) == json.dumps(b["qualifier"], sort_keys=True):
                unit = ub if ":type-" in ua else ua
                add((f"{unit} vs {dev}:house-types", field, json.dumps(a["qualifier"], sort_keys=True)),
                    "plot_or_type_variation", a, b, None, "resolve_entity_never_merge")
            elif "ambiguous" in (units.get(ua), units.get(ub)) and not any(u.endswith((":whole", ":development")) for u in (ua, ub)) \
                    and json.dumps(a["qualifier"], sort_keys=True) == json.dumps(b["qualifier"], sort_keys=True):
                pair = " vs ".join(sorted((ua, ub)))
                add((pair, field, json.dumps(a["qualifier"], sort_keys=True)), "plot_or_type_variation", a, b, None, "resolve_entity_never_merge")

    out = []
    for k, c in merged.items():
        fs = list(c["facts"].values())
        cands = c["candidates"]
        candidate = max(cands, key=lambda f: (-(f["authority_tier"] or 9), docs[f["doc_id"]].get("doc_date") or "")) if cands else None
        material = c["field"] in MATERIAL_FIELDS
        requires_human = c["type"] in ("true_conflict", "official_record_mismatch") or material or \
            (candidate is not None and any((f["authority_tier"] or 9) < (candidate["authority_tier"] or 9) for f in fs))
        downstream = {"stale_listing": "flag_listing_for_update", "official_record_mismatch": "check_current_title"}.get(c["type"])
        qk = hashlib.sha1(f"{c['unit_id']}|{c['field']}|{c['qualifier_key']}".encode()).hexdigest()[:12]
        out.append({
            "contradiction_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join(map(str, k)) + "|".join(sorted(c["facts"])))),
            "unit_id": c["unit_id"], "field": c["field"], "qualifier_key": c["qualifier_key"], "qualifier_hash": qk,
            "type": c["type"], "fact_ids": sorted(c["facts"]),
            "doc_ids": sorted({f["doc_id"] for f in fs}),
            "values": sorted({_display(f) for f in fs}),
            "candidate_fact_id": candidate["fact_id"] if candidate else None,
            "rule_applied": c["rule_applied"], "requires_human": requires_human, "status": "open",
            "agent_script_state": "do_not_quote_pending" if (c["type"] == "stale_listing" and material) else AGENT_STATE[c["type"]],
            "downstream_action": downstream,
        })
    out.sort(key=lambda c: (c["unit_id"], c["field"], c["type"]))
    return out
