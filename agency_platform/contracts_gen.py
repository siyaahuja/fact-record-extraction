"""Builds contracts 01-05 for one development from extractor output plus review actions.

01_extracted   facts (accepted by default) + open contradictions with the recommended pick
02_review_actions  reviewer actions (reject/unreject fact, resolve contradiction)
03_resolved    every fact with its resolved status, every contradiction with its resolution
04_voice_agent verified facts with citations + a do_not_state list
05_listing     listing fields: value, fact_id, verification_status verified | pending_verification
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

TYPE_PLAIN = {
    "version_supersession": "A newer version of the same document says something different",
    "true_conflict": "Two equally authoritative sources disagree",
    "unit_or_measurement_mismatch": "Same area quoted in different units or on a different basis",
    "scope_difference": "One source talks about the whole development, the other about this home",
    "plot_or_type_variation": "The figures belong to a different plot or house type",
    "stale_listing": "A portal listing is out of date versus a newer document",
    "official_record_mismatch": "A document disagrees with the official register",
}

RULE_PLAIN = {
    "same_issuer_later_supersedes": "Same issuer and document type: the later document wins.",
    "later_higher_tier_supersedes": "The later, more authoritative document wins.",
    "higher_tier_candidate_human_required": "The more authoritative source is recommended; a human must sign off.",
    "higher_tier_wins": "The more authoritative source wins.",
    "normalise_and_label": "Normalise units and label the basis; the document with a printing error is flagged.",
    "keep_both_scoped": "Keep both, each at the scope its source states. Never copy down.",
    "resolve_entity_never_merge": "These describe different plots or house types. Keep them separate.",
    "human_required": "Needs a human: check the current official record.",
}

FIELD_LABEL = {
    "price": "Price", "rent": "Rent", "tenure": "Tenure", "transaction_type": "Transaction",
    "floor_area": "Floor area", "epc_rating": "EPC rating", "parking": "Parking", "bedrooms": "Bedrooms",
    "bathrooms": "Bathrooms", "bathroom_fixture": "Bathroom fittings", "availability": "Availability",
    "finish": "Finish", "heating": "Heating",
}

TIER_LABEL = {1: "Legal instrument", 2: "Official register", 3: "Measured / signed spec", 4: "Developer instruction",
              5: "Agent particulars", 6: "Portal / CRM"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fmt_value(f: dict) -> str:
    v, q = f.get("value") or {}, f.get("qualifier") or {}
    field = f["field"]
    if field in ("price", "rent") and "amount" in v:
        s = f"£{v['amount']:,.0f}"
        if field == "price" and q.get("type"):
            s += f" ({q['type'].replace('_', ' ')})"
        if field == "rent":
            s += {"annum": " pa", "month": " pcm", "week": " pw"}.get(q.get("period"), "")
            if q.get("per") == "floor":
                s += " per floor"
        return s
    if field == "floor_area" and f.get("normalised"):
        n = f["normalised"]
        basis = q.get("basis", "unspecified")
        return f"{n['sq_ft']:,.0f} sq ft / {n['sq_m']:,.1f} sq m ({'basis not stated' if basis == 'unspecified' else basis})"
    if field == "epc_rating":
        return f"Band {v.get('band')}" + (f" ({q['type']})" if q.get("type") else "")
    if field == "parking":
        scope = (q.get("scope") or "").replace("_", " ")
        return f"{v.get('spaces')} space{'s' if v.get('spaces') != 1 else ''}" + (f" {scope}" if scope else "") + \
            (f", {v['kind']}" if v.get("kind") and v["kind"] != "unspecified" else "")
    if field in ("bedrooms", "bathrooms"):
        return str(v.get("count"))
    if field == "tenure":
        return str(v.get("tenure", "")).replace("_", " ").capitalize()
    if field == "transaction_type":
        return str(v.get("type", "")).replace("_", " ").capitalize()
    if field == "availability":
        return str(v.get("status", "")).replace("_", " ").capitalize()
    if field == "bathroom_fixture":
        room = q.get("room", "").replace("_", " ")
        return (f"{room}: " if room else "") + str(v.get("fixture", v.get("text", "")))
    parts = [f"{k}: {val}" for k, val in v.items() if k != "text"] or [str(v.get("text", ""))]
    return ", ".join(parts)


def value_key(f: dict) -> str:
    v = f.get("value") or {}
    if f["field"] == "floor_area" and f.get("normalised"):
        return f"{f['qualifier'].get('basis')}|{round(f['normalised']['sq_m'])}"
    core = {k: v[k] for k in sorted(v) if k not in ("text", "kind", "score", "certificate_date")}
    return json.dumps([f["field"], f.get("qualifier", {}).get("scope"), core], sort_keys=True)


def slot_key(f: dict) -> str:
    """What a listing line is about: price 'guide' vs 'offers' is one slot, NIA vs GIA are two."""
    keep = ("basis", "scope", "room") + (("type",) if f["field"] == "epc_rating" else ())
    q = {k: v for k, v in (f.get("qualifier") or {}).items() if k in keep}
    return f"{f['unit_id']}|{f['field']}|{json.dumps(q, sort_keys=True)}"


def citation(f: dict, docs: dict) -> dict:
    d = docs.get(f["doc_id"], {})
    return {"doc_id": f["doc_id"], "page": f["page"], "quote": f["quote"], "issuer": d.get("issuer_org"),
            "doc_type": d.get("doc_type"), "authority_tier": f.get("authority_tier"), "as_at": f.get("as_at"),
            "source": d.get("source")}


def label_contradictions(contradictions: list[dict], key: dict | None) -> dict[str, str]:
    """Map detected contradiction_id -> C01.. using the same matching the extractor's eval uses."""
    if not key:
        return {}
    try:
        from extraction.evaluate import FIELD_ALIASES
    except Exception:
        FIELD_ALIASES = {}
    out = {}
    for c in key.get("contradictions", []):
        ev_docs = {e["doc_id"] for e in c["evidence"]}
        fields = set(FIELD_ALIASES.get(c["field"], [])) or {g for f in c["field"].split("/") for g in
                                                           FIELD_ALIASES.get(f.strip(), [f.strip()])}
        dev = c["unit"].split(":")[0]
        for x in contradictions:
            if x["contradiction_id"] in out:
                continue
            if x["field"] in fields and x["unit_id"].startswith(dev) and x["type"] == c["type"] and \
                    len(ev_docs & set(x["doc_ids"])) >= min(2, len(ev_docs)):
                out[x["contradiction_id"]] = c["id"]
                break
    return out


def build_extracted(dev: dict, docs: list[dict], facts: list[dict], contradictions: list[dict], labels: dict) -> dict:
    by_id = {f["fact_id"]: f for f in facts}
    dmap = {d["doc_id"]: d for d in docs}
    out_c = []
    for c in contradictions:
        cands = []
        for fid in c["fact_ids"]:
            f = by_id.get(fid)
            if not f:
                continue
            cands.append({"fact_id": fid, "value": fmt_value(f), "unit_id": f["unit_id"], "scope": f.get("scope"),
                          "qualifier": f.get("qualifier"), "doc_error": f.get("doc_error", False),
                          **citation(f, dmap), "tier_label": TIER_LABEL.get(f.get("authority_tier"))})
        cands.sort(key=lambda x: (x["authority_tier"] or 9, -(int((x["as_at"] or "0").replace("-", "") or 0))))
        rec = c.get("candidate_fact_id")
        out_c.append({
            "contradiction_id": c["contradiction_id"], "label": labels.get(c["contradiction_id"]),
            "unit_id": c["unit_id"], "field": c["field"], "field_label": FIELD_LABEL.get(c["field"], c["field"]),
            "type": c["type"], "type_plain": TYPE_PLAIN.get(c["type"], c["type"]),
            "fact_ids": c["fact_ids"], "candidates": cands, "requires_human": c.get("requires_human"),
            "recommended": {"fact_id": rec, "value": fmt_value(by_id[rec]) if rec in by_id else None,
                            "action": "choose_fact" if rec else "keep_both_scoped",
                            "rule_applied": c.get("rule_applied"),
                            "reason": RULE_PLAIN.get(c.get("rule_applied"), c.get("rule_applied"))},
            "agent_script_state": c.get("agent_script_state"), "downstream_action": c.get("downstream_action"),
            "status": "open",
        })
    return {"contract": "01_extracted", "development_id": dev["development_id"], "development": dev,
            "generated_at": now(), "documents": docs,
            "facts": [{**f, "review_status": "accepted", "display_value": fmt_value(f)} for f in facts],
            "contradictions": out_c}


def build_resolved(extracted: dict, actions: list[dict]) -> dict:
    facts = {f["fact_id"]: dict(f) for f in extracted["facts"]}
    rejected = set()
    for a in actions:
        if a["action"] == "reject_fact":
            rejected.add(a["fact_id"])
        elif a["action"] == "unreject_fact":
            rejected.discard(a["fact_id"])
    resolutions = {}
    for a in actions:
        if a["action"] == "resolve_contradiction":
            resolutions[a["contradiction_id"]] = a
        elif a["action"] == "reopen_contradiction":
            resolutions.pop(a["contradiction_id"], None)

    chosen, superseded, scoped_ok = set(), set(), set()
    contradictions = []
    for c in extracted["contradictions"]:
        c = dict(c)
        a = resolutions.get(c["contradiction_id"])
        live = [fid for fid in c["fact_ids"] if fid in facts and fid not in rejected]
        if a:
            mode = a["resolution"]
            pick = a.get("chosen_fact_id") if mode == "choose_fact" else c["recommended"]["fact_id"]
            if mode == "accept_recommendation" and not pick:
                mode = "keep_both_scoped"
            if mode == "keep_both_scoped":
                scoped_ok.update(live)
                c["resolved_fact_id"] = None
            else:
                win_key = value_key(facts[pick]) if pick in facts else None
                for fid in live:
                    (chosen if value_key(facts[fid]) == win_key else superseded).add(fid)
                c["resolved_fact_id"] = pick
            c.update(status="resolved", resolution=mode, resolved_by=a.get("reviewer"), resolved_at=a.get("timestamp"))
        contradictions.append(c)

    # A reviewer's pick wins its slot: same-slot facts with another value are superseded too.
    slots = defaultdict(list)
    for fid, f in facts.items():
        slots[slot_key(f)].append(fid)
    for fid in list(chosen):
        win = value_key(facts[fid])
        for other in slots[slot_key(facts[fid])]:
            if other not in rejected and other not in chosen:
                (chosen if value_key(facts[other]) == win else superseded).add(other)
    superseded -= chosen

    dead = rejected | superseded
    for c in contradictions:
        if c["status"] == "open":
            live = [fid for fid in c["fact_ids"] if fid in facts and fid not in dead]
            if len({value_key(facts[fid]) for fid in live}) < 2:
                c.update(status="resolved", resolution="auto_no_remaining_conflict",
                         resolved_fact_id=live[0] if len(live) == 1 else None)

    hard_states = ("do_not_quote_conflicting", "do_not_quote_pending")
    blocking = defaultdict(list)
    for c in contradictions:
        if c["status"] == "open" and c["agent_script_state"] in hard_states:
            for fid in c["fact_ids"]:
                if fid not in dead:
                    blocking[fid].append(c)
    status = {}
    for fid in facts:
        if fid in rejected:
            status[fid] = "rejected"
        elif fid in superseded:
            status[fid] = "superseded"
        elif fid in chosen:
            status[fid] = "verified"
        elif blocking.get(fid):
            status[fid] = "conflicting" if any(c["agent_script_state"] == "do_not_quote_conflicting"
                                               for c in blocking[fid]) else "pending"
        else:
            status[fid] = "verified"
    # A slot with an unresolved conflict is not verified anywhere in it, even for facts outside the contradiction.
    for key, fids in slots.items():
        held = [status[f] for f in fids if status[f] in ("pending", "conflicting")]
        if held and not any(f in chosen for f in fids):
            for f in fids:
                if status[f] == "verified":
                    status[f] = "conflicting" if "conflicting" in held else "pending"
                    blocking[f] = sorted({id(c): c for x in fids for c in blocking.get(x, [])}.values(), key=lambda c: c["contradiction_id"])
    out_facts = []
    for fid, f in facts.items():
        f["review_status"] = "rejected" if fid in rejected else "accepted"
        f["status"] = status[fid]
        f["resolved_by_review"] = fid in chosen
        f["open_contradictions"] = [c["label"] or c["contradiction_id"][:8] for c in blocking.get(fid, [])]
        out_facts.append(f)
    return {"contract": "03_resolved", "development_id": extracted["development_id"], "generated_at": now(),
            "facts": out_facts, "contradictions": contradictions}


def _best(facts: list[dict]) -> dict:
    return sorted(facts, key=lambda f: (f.get("authority_tier") or 9, "".join(reversed(f.get("as_at") or "")), f["fact_id"]))[0]


def build_voice(resolved: dict, extracted: dict) -> dict:
    dmap = {d["doc_id"]: d for d in extracted["documents"]}
    units = defaultdict(list)
    slots = defaultdict(list)
    for f in resolved["facts"]:
        slots[slot_key(f)].append(f)
    do_not_state = []
    for key, fs in sorted(slots.items()):
        ver = [f for f in fs if f["status"] == "verified"]
        if ver:
            seen = set()
            for f in sorted(ver, key=lambda f: (f.get("authority_tier") or 9, f["fact_id"])):
                vk = value_key(f)
                if vk in seen:
                    continue
                seen.add(vk)
                units[f["unit_id"]].append({"fact_id": f["fact_id"], "field": f["field"], "qualifier": f["qualifier"],
                                            "scope": f.get("scope"), "value": f["value"], "statement": fmt_value(f),
                                            "citation": citation(f, dmap)})
        else:
            blocked = [f for f in fs if f["status"] in ("pending", "conflicting")]
            if blocked:
                f = blocked[0]
                do_not_state.append({"unit_id": f["unit_id"], "field": f["field"], "qualifier": f["qualifier"],
                                     "reason": f["status"], "contradictions": sorted({c for b in blocked for c in b["open_contradictions"]}),
                                     "say_instead": "I can't confirm that yet; an agent will come back to you."})
    return {"contract": "04_voice_agent", "development_id": resolved["development_id"], "generated_at": now(),
            "units": [{"unit_id": u, "verified_facts": v} for u, v in sorted(units.items())],
            "do_not_state": do_not_state}


LISTING_FIELDS = ["price", "transaction_type", "tenure", "floor_area", "bedrooms", "bathrooms", "epc_rating", "parking",
                  "rent", "availability"]


def build_listing(resolved: dict, extracted: dict, primary_unit: str | None) -> dict:
    slots = defaultdict(list)
    for f in resolved["facts"]:
        if f["field"] in LISTING_FIELDS and f["status"] != "rejected":
            slots[slot_key(f)].append(f)
    units = defaultdict(list)
    for key, fs in slots.items():
        unit = fs[0]["unit_id"]
        ver = [f for f in fs if f["status"] == "verified"]
        live = [f for f in fs if f["status"] in ("pending", "conflicting")]
        if not ver and not live:
            continue
        if ver:
            f = _best(ver)
            entry = {"value": fmt_value(f), "raw_value": f["value"], "fact_id": f["fact_id"],
                     "verification_status": "verified", "source": {"doc_id": f["doc_id"], "page": f["page"]}}
        else:
            entry = {"value": None, "raw_value": None, "fact_id": None, "verification_status": "pending_verification",
                     "open_contradictions": sorted({c for x in live for c in x["open_contradictions"]})}
        q = {k: v for k, v in fs[0]["qualifier"].items() if k in ("basis", "scope", "type", "period", "per")}
        label = FIELD_LABEL.get(fs[0]["field"], fs[0]["field"])
        if fs[0]["field"] == "floor_area":
            label += f" ({q.get('basis', '')})"
        elif fs[0]["field"] == "parking" and q.get("scope"):
            label += f" ({q['scope'].replace('_', ' ')})"
        units[unit].append({"field": fs[0]["field"], "label": label, "qualifier": q, **entry})
    order = {f: i for i, f in enumerate(LISTING_FIELDS)}
    out_units = []
    for u, fields in units.items():
        fields.sort(key=lambda x: (order[x["field"]], x["label"]))
        out_units.append({"unit_id": u, "primary": u == primary_unit, "fields": fields})
    out_units.sort(key=lambda x: (not x["primary"], x["unit_id"]))
    return {"contract": "05_listing", "development_id": resolved["development_id"], "generated_at": now(),
            "primary_unit_id": primary_unit, "units": out_units}
