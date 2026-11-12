"""Build the harness contracts from a real pipeline run.

  python3 contracts/build.py            # 01 from out/ (+ seeds 02 if missing), then 03/04/05 from 01 + 02
  python3 contracts/build.py --reseed   # also regenerate the demo review actions in 02

01_extracted.json       facts + contradictions as extracted (facts accepted by default, contradictions open)
02_review_actions.json  human actions: reject a fact, resolve a contradiction (hand-editable; seeded with demo choices)
03_resolved.json        01 after applying 02, with before/after for C01 and C06
04_voice_agent.json     per unit: verified, quotable statements with citations + do_not_state for open contradictions
05_listing.json         per unit: listing fields with value, display, fact_id, verification_status
"""
from __future__ import annotations

import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from extraction.evaluate import FIELD_ALIASES, _matches, _parse_evidence  # noqa: E402

HERE = os.path.join(ROOT, "contracts")
OUT = os.path.join(ROOT, "out")
KEY = os.path.join(ROOT, "sample_data", "contradictions.json")
DEVELOPMENTS = {"kelso-villa-ba1-3au": "kelso-villa", "st-huberts-close-gerrards-cross": "59-st-huberts-close"}
LISTING_UNITS = {"kelso-villa": "kelso-villa-ba1-3au:whole", "59-st-huberts-close": "st-huberts-close-gerrards-cross:no-59"}
KEEP_BOTH_TYPES = {"scope_difference", "plot_or_type_variation"}
SAFE_PHRASING = {
    "price": "The price is being confirmed with the agent; I can arrange for them to call you.",
    "rent": "The rent is being confirmed with the agent.",
    "floor_area": "The floor area is being verified against the measured survey; I can send the confirmed figure.",
    "parking": "The parking allocation is being confirmed.",
    "epc_rating": "The EPC rating is being checked against the official register.",
    "transaction_type": "Whether it is for sale or to let is being confirmed with the agent.",
    "bathroom_fixture": "The bathroom specification for this home is being confirmed.",
    "bedrooms": "The bedroom count for this home is being confirmed.",
    "availability": "Availability is being confirmed with the agent.",
}
# Demo choices for the answer-key contradictions (see sample_data/contradictions.json expected_resolution).
DEMO = {
    "C01": ("accept_recommendation", None, "Same agent, later particulars (Oct 2026) supersede April."),
    "C02": ("choose_fact", {"doc_id": "carterjonas-f8692efa", "field": "floor_area", "basis": "NIA", "page": 1},
            "April row prints 185 sq m next to 2,700 sq ft: document error. Use October's 1,990 sq ft (185 m²) NIA."),
    "C03": ("accept_recommendation", None, "Measured survey (tier 3, RICS basis stated) over brochure NIA."),
    "C04": ("accept_recommendation", None, "Measured survey GIA over brochure GIA."),
    "C05": ("keep_both_scoped", None, "Brochure 468 sq ft has no stated basis; survey 461 sq ft is NIA. Keep both, labelled."),
    "C06": ("choose_fact", {"doc_id": "syn-kv-survey", "field": "parking", "page": 1, "spaces": 5},
            "Survey on site 9 Sep 2026: five bays usable, bay 6 is bin store. Confirmed with agent."),
    "C07": ("keep_both_scoped", None, "One space per floor letting allowance vs six spaces for the building: different scopes."),
    "C08": ("choose_fact", {"doc_id": "syn-kv-survey", "field": "epc_rating"},
            "Checked the EPC register: certificate 9417-3082-6651-2049-7735 is band C."),
    "C09": ("accept_recommendation", None, "Solicitor's formal instruction (3 Nov 2026) supersedes the April brochure."),
    "C10": ("keep_both_scoped", None, "Development-wide finishes claim stays on the development, not on No. 59."),
    "C11": ("keep_both_scoped", None, "No. 59 is type E; type D facts stay on type D."),
}
REVIEWER = {"id": "agent-demo", "name": "Demo Reviewer (sales agency)"}
DEMO_TIME = "2026-11-12T21:30:00Z"


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def dump(name, obj):
    with open(os.path.join(HERE, name), "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def fmt_value(f) -> str:
    v, n = f["value"], f.get("normalised")
    if f["field"] in ("price", "rent"):
        s = f"£{v['amount']:,.0f}"
        t = f["qualifier"].get("type")
        return s + (f" {t.replace('_', ' ')}" if t and f["field"] == "price" else "") + (
            f" per {f['qualifier'].get('period')}" if f["field"] == "rent" and f["qualifier"].get("period") else "")
    if f["field"] == "floor_area":
        basis = f["qualifier"].get("basis")
        b = "" if basis == "unspecified" else f" {basis}"
        return f"{n['sq_ft']:,.0f} sq ft ({n['sq_m']:,.1f} sq m){b}" + (" [basis not stated]" if basis == "unspecified" else "")
    if f["field"] == "epc_rating":
        return f"EPC {v['band']}" + (f" ({v['score']})" if v.get("score") else "")
    if f["field"] == "parking":
        return f"{v['spaces']} {'allocated ' if v.get('kind') == 'allocated' else ''}parking space{'s' if v['spaces'] != 1 else ''} ({f['qualifier'].get('scope', 'total').replace('_', ' ')})"
    if f["field"] == "tenure":
        return v["tenure"].replace("_", " ").capitalize()
    if f["field"] == "transaction_type":
        return v["type"].replace("_", " ").capitalize()
    if f["field"] in ("bedrooms", "bathrooms"):
        return f"{v['count']} {f['field'] if v['count'] != 1 else f['field'][:-1]}"
    if f["field"] == "listed_status":
        return f"Grade {v.get('grade')} listed"
    if f["field"] == "bathroom_fixture":
        return v.get("text") or v.get("fixture")
    if f["field"] == "availability":
        return v.get("status", "").replace("_", " ")
    return json.dumps(v)


# ------------------------------------------------------------------ 01

def build_extracted():
    facts = load_jsonl(os.path.join(OUT, "facts.jsonl"))
    docs = {d["doc_id"]: d for d in load_jsonl(os.path.join(OUT, "documents.jsonl"))}
    detected = load_jsonl(os.path.join(OUT, "contradictions.jsonl"))
    with open(KEY) as f:
        key = json.load(f)
    by_id = {f["fact_id"]: f for f in facts}

    contradictions, used = [], set()
    for c in key["contradictions"]:
        fields = [g for x in c["field"].split("/") for g in FIELD_ALIASES.get(x.strip(), [x.strip()])]
        checks = [{"doc_id": e["doc_id"], "page": e["page"], "field": fld, **chk}
                  for e in c["evidence"] for fld in fields for chk in _parse_evidence(fld, c.get("qualifier") or {}, e["value"])]
        evidence_ids = {f["fact_id"] for f in facts if any(_matches(f, chk) for chk in checks)}
        ev_docs = {e["doc_id"] for e in c["evidence"]}
        recs = [d for d in detected if d["field"] in fields and d["type"] == c["type"]
                and len(ev_docs & set(d["doc_ids"])) >= min(2, len(ev_docs))]
        members = sorted({i for d in recs for i in d["fact_ids"]} & evidence_ids) or sorted(evidence_ids)
        if len(members) < 2:  # the detection holds the other side (e.g. the unit-level fact)
            members = sorted({i for d in recs for i in d["fact_ids"]} | evidence_ids)
        used.update(d["contradiction_id"] for d in recs)
        contradictions.append(_contradiction(c["id"], c["type"], fields[0], c["unit"], members, by_id, recs, docs))
    extra = [d for d in detected if d["contradiction_id"] not in used]
    for i, d in enumerate(extra, 1):
        contradictions.append(_contradiction(f"D{i:02d}", d["type"], d["field"], d["unit_id"], sorted(d["fact_ids"]), by_id, [d], docs))

    out = {"contract": "01_extracted", "version": 1,
           "source": "real pipeline output: out/facts.jsonl, out/contradictions.jsonl, out/documents.jsonl (rules extractor)",
           "developments": {}}
    for dev_id, name in DEVELOPMENTS.items():
        dev_facts = [_fact(f, docs) for f in facts if f["development_id"] == dev_id]
        ids = {f["id"] for f in dev_facts}
        out["developments"][name] = {
            "development_id": dev_id,
            "documents": [{k: d[k] for k in ("doc_id", "doc_type", "authority_tier", "issuer_org", "doc_date", "doc_date_source", "page_count", "unit_id")}
                          for d in docs.values() if d.get("development_id") == dev_id],
            "facts": dev_facts,
            "contradictions": [c for c in contradictions if set(c["fact_ids"]) & ids],
        }
    return out


def _fact(f, docs):
    d = docs[f["doc_id"]]
    return {"id": f["fact_id"], "unit_id": f["unit_id"], "field": f["field"], "qualifier": f["qualifier"],
            "basis": f["qualifier"].get("basis"), "scope": f["qualifier"].get("scope") or f.get("scope"),
            "value_raw": f["value_raw"], "value": f["value"], "display": fmt_value(f),
            "normalised": f.get("normalised"), "doc_error": f["doc_error"],
            "doc_id": f["doc_id"], "doc_type": d["doc_type"], "authority_tier": f["authority_tier"], "doc_date": d["doc_date"],
            "issuer": d.get("issuer_org"), "page": f["page"], "quote": f["quote"], "quote_source": f.get("quote_source"),
            "extraction_method": f["extraction_method"], "status": "accepted"}


def _contradiction(cid, ctype, field, unit, members, by_id, recs, docs):
    keep_both = ctype in KEEP_BOTH_TYPES or (ctype == "unit_or_measurement_mismatch" and
                                             len({by_id[m]["qualifier"].get("basis") for m in members}) > 1 and
                                             not any(by_id[m]["doc_error"] for m in members))
    rec, reason = None, "Different scopes or bases: keep both, each labelled with its own scope."
    if not keep_both:
        cand = next((d["candidate_fact_id"] for d in recs if d.get("candidate_fact_id") in members), None)
        ranked = sorted(members, key=lambda m: (by_id[m]["doc_error"], by_id[m]["authority_tier"] or 9,
                                                 "".join(chr(255 - ord(ch)) for ch in str(by_id[m]["as_at"] or ""))))
        rec = cand or ranked[0]
        r, others = by_id[rec], [by_id[m] for m in members if m != rec]
        rd = docs[r["doc_id"]]
        if ctype == "official_record_mismatch":
            reason = "Official record (or a document citing it) differs from marketing; a human checks the register."
        elif all(o["authority_tier"] == r["authority_tier"] for o in others):
            reason = f"Same authority tier ({r['authority_tier']}): newest document wins ({rd['doc_type']}, {r['as_at']})."
        else:
            reason = f"Highest authority: {rd['doc_type']} (tier {r['authority_tier']}, {r['as_at']}) over tier " + \
                     ", ".join(sorted({str(o['authority_tier']) for o in others if o['authority_tier'] != r['authority_tier']})) + "."
        if any(by_id[m]["doc_error"] for m in members):
            reason += " A member has doc_error (printed units disagree)."
    return {"id": cid, "type": ctype, "field": field, "unit_id": unit,
            "scope": sorted({str(by_id[m]["qualifier"].get("scope") or by_id[m]["unit_id"].split(":")[-1]) for m in members}),
            "fact_ids": members, "values": [f"{fmt_value(by_id[m])} [{by_id[m]['doc_id']} p{by_id[m]['page']}]" for m in members],
            "recommended_fact_id": rec, "recommendation_reason": reason,
            "requires_human": True, "status": "open"}


# ------------------------------------------------------------------ 02

def seed_review(extracted):
    facts = {f["id"]: f for dev in extracted["developments"].values() for f in dev["facts"]}
    actions = []
    for c in _all_contradictions(extracted):
        if c["id"] not in DEMO:
            continue
        kind, pick, why = DEMO[c["id"]]
        a = {"action": "resolve_contradiction", "contradiction_id": c["id"], "resolution": kind,
             "reviewer": REVIEWER, "at": DEMO_TIME, "note": why}
        if kind == "choose_fact":
            want = dict(pick)
            a["fact_id"] = next(m for m in c["fact_ids"] if all(
                (facts[m].get(k) if k in ("doc_id", "field", "page", "basis") else facts[m]["value"].get(k)) == v for k, v in want.items()))
        actions.append(a)
    oct_partial = next((f for f in facts.values() if f["doc_id"] == "carterjonas-f8692efa" and f["field"] == "transaction_type"
                        and f["value"].get("type") == "for_sale"), None)
    if oct_partial:
        actions.insert(0, {"action": "reject_fact", "fact_id": oct_partial["id"], "reviewer": REVIEWER, "at": DEMO_TIME,
                           "note": "Partial read of the 'For Sale or To Let' banner; the full banner is extracted separately."})
    return {
        "contract": "02_review_actions", "version": 1,
        "shapes": {
            "reject_fact": {"action": "reject_fact", "fact_id": "<fact id>", "reviewer": {"id": "str", "name": "str"},
                            "at": "ISO-8601 UTC", "note": "optional reason"},
            "resolve_contradiction": {"action": "resolve_contradiction", "contradiction_id": "C01..",
                                      "resolution": "accept_recommendation | choose_fact | keep_both_scoped",
                                      "fact_id": "<required when resolution = choose_fact; must be a member>",
                                      "reviewer": {"id": "str", "name": "str"}, "at": "ISO-8601 UTC", "note": "why (audit)"},
        },
        "rules": ["Facts are accepted by default; only rejections are recorded.",
                  "Actions apply in order; a later action on the same id replaces an earlier one.",
                  "Contradictions without an action stay open and block their field in 04/05."],
        "actions": actions,
    }


# ------------------------------------------------------------------ 03

def _all_contradictions(extracted):
    seen, out = set(), []
    for dev in extracted["developments"].values():
        for c in dev["contradictions"]:
            if c["id"] not in seen:
                seen.add(c["id"])
                out.append(c)
    return out


def apply_review(extracted, review):
    res = copy.deepcopy(extracted)
    res["contract"], res["source"] = "03_resolved", "01_extracted.json + 02_review_actions.json"
    facts = {f["id"]: f for dev in res["developments"].values() for f in dev["facts"]}
    cons = {}
    for dev in res["developments"].values():
        for c in dev["contradictions"]:
            cons.setdefault(c["id"], []).append(c)
    for f in facts.values():
        f["history"] = [{"status": "accepted", "by": "system", "at": None, "note": "accepted by default"}]
    resolutions = {}
    for a in review["actions"]:
        if a["action"] == "reject_fact" and a["fact_id"] in facts:
            f = facts[a["fact_id"]]
            f["status"] = "rejected"
            f["history"].append({"status": "rejected", "by": a["reviewer"]["id"], "at": a["at"], "note": a.get("note")})
        elif a["action"] == "resolve_contradiction" and a["contradiction_id"] in cons:
            resolutions[a["contradiction_id"]] = a
    for cid, copies in cons.items():
        a = resolutions.get(cid)
        if not a:
            continue
        c = copies[0]
        winner = c["recommended_fact_id"] if a["resolution"] == "accept_recommendation" else a.get("fact_id")
        if a["resolution"] == "choose_fact" and winner not in c["fact_ids"]:
            raise SystemExit(f"{cid}: chosen fact is not a member")
        for cc in copies:
            cc["status"] = "resolved"
            cc["resolution"] = {"kind": a["resolution"], "winning_fact_id": winner, "reviewer": a["reviewer"], "at": a["at"], "note": a.get("note")}
        if a["resolution"] == "keep_both_scoped":
            continue
        wf = facts[winner]
        for m in c["fact_ids"]:
            f = facts[m]
            if f["status"] == "rejected":
                continue
            same = m == winner or (f["value"] == wf["value"] and not f["doc_error"])
            new = "verified" if same else "superseded"
            f["status"] = new
            f["history"].append({"status": new, "by": a["reviewer"]["id"], "at": a["at"], "via": cid,
                                 "note": "winner" if m == winner else "corroborates winner" if same else f"superseded by {winner}"})
    open_ids = {fid for cid, copies in cons.items() if copies[0]["status"] == "open" for fid in copies[0]["fact_ids"]}
    for f in facts.values():
        if f["status"] == "accepted":
            if f["id"] in open_ids:
                f["blocked_by_open_contradiction"] = True
            else:
                f["status"] = "verified"
                f["history"].append({"status": "verified", "by": "system", "at": DEMO_TIME,
                                     "note": "accepted and not in any open contradiction"})
    before = {c["id"]: c for c in _all_contradictions(extracted)}
    by_before = {f["id"]: f for dev in extracted["developments"].values() for f in dev["facts"]}
    res["before_after"] = {}
    for cid in ("C01", "C06"):
        if cid in before:
            res["before_after"][cid] = {
                "before": {"contradiction": before[cid],
                           "facts": [{k: by_before[m][k] for k in ("id", "display", "doc_id", "page", "status")} for m in before[cid]["fact_ids"]]},
                "after": {"contradiction": cons[cid][0],
                          "facts": [{k: facts[m][k] for k in ("id", "display", "doc_id", "page", "status")} for m in before[cid]["fact_ids"]]},
            }
    return res


# ------------------------------------------------------------------ 04 / 05

def _citation(f):
    return {"fact_id": f["id"], "doc_id": f["doc_id"], "doc_type": f["doc_type"], "issuer": f["issuer"],
            "page": f["page"], "quote": f["quote"], "doc_date": f["doc_date"]}


def voice_agent(resolved):
    out = {"contract": "04_voice_agent", "version": 1,
           "rules": ["Only state facts listed under 'statements'; cite the document when asked.",
                     "Never state a value for a field in 'do_not_state'; use the safe phrasing instead."],
           "units": {}}
    for name, dev in resolved["developments"].items():
        units = sorted({f["unit_id"] for f in dev["facts"]})
        for unit in units:
            facts = [f for f in dev["facts"] if f["unit_id"] == unit]
            verified = [f for f in facts if f["status"] == "verified"]
            open_c = [c for c in dev["contradictions"] if c["status"] == "open" and set(c["fact_ids"]) & {f["id"] for f in facts}]
            out["units"][unit] = {
                "development": name,
                "statements": [{"field": f["field"], "scope": f["scope"], "say": _say(f), "citation": _citation(f)} for f in verified],
                "do_not_state": [{"field": c["field"], "contradiction_id": c["id"], "type": c["type"],
                                  "conflicting_values": c["values"], "safe_phrasing": SAFE_PHRASING.get(c["field"], "That detail is being confirmed.")}
                                 for c in open_c],
            }
    return out


def _say(f):
    label = {"price": "Price", "rent": "Rent", "floor_area": "Floor area", "epc_rating": "EPC rating", "parking": "Parking",
             "tenure": "Tenure", "transaction_type": "Offered", "bedrooms": "Bedrooms", "bathrooms": "Bathrooms",
             "listed_status": "Listing", "bathroom_fixture": "Bathrooms", "availability": "Availability"}.get(f["field"], f["field"])
    scope = f["scope"] if f["scope"] not in (None, "whole", "unit", "building") else None
    return f"{label}: {f['display']}" + (f" ({scope.replace('_', ' ').replace(':', ' ')})" if scope else "") + \
           f", per the {f['doc_type'].replace('_', ' ')} dated {f['doc_date']}."


LISTING_FIELDS = {
    "price": lambda f: f["field"] == "price",
    "tenure": lambda f: f["field"] == "tenure",
    "transaction_type": lambda f: f["field"] == "transaction_type",
    "net_area": lambda f: f["field"] == "floor_area" and f["basis"] == "NIA" and f["scope"] == "whole",
    "gross_area": lambda f: f["field"] == "floor_area" and f["basis"] == "GIA" and f["scope"] == "whole",
    "stated_area": lambda f: f["field"] == "floor_area" and f["basis"] == "unspecified" and f["scope"] == "whole",
    "epc": lambda f: f["field"] == "epc_rating",
    "parking": lambda f: f["field"] == "parking" and f["qualifier"].get("scope", "total") == "total",
    "bedrooms": lambda f: f["field"] == "bedrooms",
    "availability": lambda f: f["field"] == "availability" and f["qualifier"].get("scope", "whole") == "whole",
}


def listing(resolved):
    out = {"contract": "05_listing", "version": 1,
           "rules": ["pending_verification fields carry no value: show 'Pending verification'.",
                     "Areas: net (NIA) and gross (GIA) are separate; an area with no stated basis is 'stated_area', never net.",
                     "'property' uses the team catalogue keys (work/hamptons_e14_2dr_lettings.json); unverified values are null."],
           "listings": {}}
    for name, unit in LISTING_UNITS.items():
        dev = resolved["developments"][name]
        facts = [f for f in dev["facts"] if f["unit_id"] == unit]
        open_c = [c for c in dev["contradictions"] if c["status"] == "open"]
        fields = {}
        for key, pred in LISTING_FIELDS.items():
            cands = [f for f in facts if pred(f)]
            blocking = [c["id"] for c in open_c if set(c["fact_ids"]) & {f["id"] for f in cands}]
            verified = sorted([f for f in cands if f["status"] == "verified"],
                              key=lambda f: (f["authority_tier"] or 9, "".join(chr(255 - ord(ch)) for ch in str(f["doc_date"]))))
            if blocking or not verified:
                pending = bool(blocking) or any(f["status"] == "accepted" for f in cands)
                fields[key] = {"value": None, "display": "Pending verification" if pending else None,
                               "fact_id": None, "verification_status": "pending_verification" if pending else "not_stated",
                               "blocked_by": blocking}
                continue
            f = verified[0]
            val = f["normalised"] if f["field"] == "floor_area" else f["value"]
            fields[key] = {"value": val, "display": f["display"], "fact_id": f["id"], "verification_status": "verified",
                           "citation": _citation(f)}
        features = [{"text": f["display"], "fact_id": f["id"], "verification_status": "verified"}
                    for f in facts if f["status"] == "verified" and f["field"] in ("listed_status", "bathroom_fixture", "bathrooms")]
        fields["key_features"] = {"value": [x["text"] for x in features], "items": features,
                                  "verification_status": "verified" if features else "not_stated"}
        out["listings"][name] = {"unit_id": unit, "fields": fields, "property": _team_property(name, unit, fields, dev)}
    return out


def _team_property(name, unit, fields, dev):
    v = lambda k: fields[k]["value"]  # noqa: E731
    price = v("price")
    tt = (v("transaction_type") or {}).get("type")
    docs = [d for d in dev["documents"] if d["unit_id"] in (unit, unit.split(":")[0] + ":whole")]
    agent = sorted(docs, key=lambda d: str(d["doc_date"]))[-1] if docs else {}
    return {
        "source_url": None, "property_id": name, "reference": unit, "agency": agent.get("issuer_org"), "branch": None,
        "status": {"for_sale": "For sale", "to_let": "To let", "for_sale_or_to_let": "For sale or to let"}.get(tt),
        "availability": (v("availability") or {}).get("status"), "live_date": agent.get("doc_date"),
        "price": fields["price"]["display"] if price else "Pending verification", "price_value": int(price["amount"]) if price else None,
        "address": {"display": name.replace("-", " ").title()}, "property_type": None,
        "transaction_type": {"for_sale": "sales", "to_let": "lettings"}.get(tt, tt),
        "bedrooms": (v("bedrooms") or {}).get("count"), "bathrooms": None, "showers": None, "reception_rooms": None,
        "furnishing": None, "description": None, "key_features": v("key_features"), "tags": [],
        "council_tax_band": None, "security_deposit": None, "images": [], "floorplans": [],
        "epc": {"rating": (v("epc") or {}).get("band")} if v("epc") else {}, "image_data": [],
        "fact_provenance": {k: fields[k].get("fact_id") for k in fields if k != "key_features"},
        "verification_status": {k: fields[k]["verification_status"] for k in fields},
    }


def main(argv):
    extracted = build_extracted()
    dump("01_extracted.json", extracted)
    review_path = os.path.join(HERE, "02_review_actions.json")
    if "--reseed" in argv or not os.path.exists(review_path):
        dump("02_review_actions.json", seed_review(extracted))
    with open(review_path) as f:
        review = json.load(f)
    resolved = apply_review(extracted, review)
    dump("03_resolved.json", resolved)
    dump("04_voice_agent.json", voice_agent(resolved))
    dump("05_listing.json", listing(resolved))
    n_f = sum(len(d["facts"]) for d in extracted["developments"].values())
    print(f"contracts: {n_f} facts, {len(_all_contradictions(extracted))} contradictions, {len(review['actions'])} review actions")


if __name__ == "__main__":
    main(sys.argv[1:])
