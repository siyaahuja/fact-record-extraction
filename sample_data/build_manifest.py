import json, hashlib, os, subprocess
K="kelso-villa-ba1-3au"; S="st-huberts-close-gerrards-cross"
docs=[
 dict(doc_id="carterjonas-98889981",file="real/kelso-villa_april-2026_to-let_carterjonas-98889981.pdf",development=K,unit=f"{K}:whole (+ {K}:lower-ground)",doc_type="particulars",issuer="Carter Jonas",issuer_role="letting_agent",date="2026-04",date_source="manual (spec; not printed)",authority_tier=5,synthetic=False,version_label="april_2026",has_text_layer=False,
      description="Real 'To Let – Lower Ground Floor' particulars. LG 468 sq ft (43.45 sq m), £9,400 pa per floor, one parking space per floor, freehold offers £700,000, EPC B; 'Total (ALL FLOORS) 185 | 2,700' row error."),
 dict(doc_id="carterjonas-f8692efa",file="real/kelso-villa_october-2026_for-sale_carterjonas-f8692efa.pdf",development=K,unit=f"{K}:whole",doc_type="particulars",issuer="Carter Jonas",issuer_role="sales_agent",date="2026-10",date_source="manual (spec; not printed)",authority_tier=5,synthetic=False,version_label="october_2026",supersedes_doc_id="carterjonas-98889981",has_text_layer=False,
      description="Real 'For Sale – Freehold Offices' particulars. 1,990 sq ft (185 m2) NIA, 2,700 sq ft GIA, £600,000 guide, 6 parking spaces total, EPC B, one floor remaining to let."),
 dict(doc_id="struttparker-a45c02cc",file="real/59-st-huberts-close_5bed_struttparker-a45c02cc.pdf",development=S,unit=f"{S}:no-59",doc_type="particulars",issuer="Strutt & Parker",issuer_role="sales_agent",date="2026-04",date_source="printed ('Particulars prepared April'; year from file metadata 2026-05-06)",authority_tier=5,synthetic=False,has_text_layer=True,
      description="Real brochure for No. 59: 5 bed detached, 5 receptions, principal en suite BATHROOM + guest en suite shower room, 2,848 sq ft (264.6 sq m), guide £1,458,000, no onward chain. No EPC or tenure printed. Some text Caesar-shifted (+29) by a broken font."),
 dict(doc_id="struttparker-92092382",file="real/st-huberts-close_4bed_struttparker-92092382.pdf",development=S,unit=f"{S}:4-bed-unnumbered",doc_type="particulars",issuer="Strutt & Parker",issuer_role="sales_agent",date="2025-11",date_source="printed ('Particulars prepared November 2025')",authority_tier=5,synthetic=False,has_text_layer=True,
      description="Real brochure for a DIFFERENT, unnumbered 4-bed house in St Huberts Close: 2,098 sq ft (194.9 sq m) incl. garage, guide £1,250,000, freehold, EPC C, council tax G, double garage."),
 dict(doc_id="syn-kv-survey",file="synthetic/kelso-villa_measured-survey_holloway-reid_2026-09.pdf",development=K,unit=f"{K}:whole + per-floor units",doc_type="measured_survey",issuer="Holloway & Reid (fictional)",issuer_role="architect",date="2026-09-18",date_source="printed",authority_tier=3,synthetic=True,pages=3,
      description="Measured survey, 3 pages: schedule of areas + site plan (p1), drawn floor plans LG/G (p2) and 1st/2nd (p3). NIA 177.6 m2 / 1,912 sq ft; GIA 248.2 m2 / 2,672 sq ft; LG NIA 461 sq ft; 6 marked parking bays."),
 dict(doc_id="syn-kv-epc",file="synthetic/kelso-villa_epc-nondomestic_2026-08.pdf",development=K,unit=f"{K}:whole",doc_type="epc_certificate",issuer="EPC register (fictional assessor, Avonvale Energy Surveys)",issuer_role="official_register",date="2026-09-02",date_source="register",register_date="2026-11-10",authority_tier=2,synthetic=True,pages=1,
      description="Non-domestic EPC: band C (asset rating 58), potential B, total useful floor area 239 m2 (EPC basis), certificate dated 2 Sept 2026."),
 dict(doc_id="syn-kv-title",file="synthetic/kelso-villa_land-registry-title-summary_2026-11.pdf",development=K,unit=f"{K}:whole",doc_type="land_registry_title_extract",issuer="HM Land Registry (fictional title ST482917)",issuer_role="official_register",date="2026-11-10",date_source="register",register_date="2026-11-10",authority_tier=2,synthetic=True,pages=1,
      description="Title summary: freehold, title absolute; 6 parking spaces in the title; office-use restrictive covenant; notice of 10-year lease of the LOWER GROUND FLOOR dated 1 Sept 2026 (with parking space 1)."),
 dict(doc_id="syn-kv-listing",file="synthetic/kelso-villa_portal-listing-snapshot_2026-11.pdf",development=K,unit=f"{K}:whole (+ lower-ground)",doc_type="portal_listing",issuer="PropNest Commercial (fictional portal)",issuer_role="sales_agent",date="2026-11-09",date_source="printed (capture time)",authority_tier=6,synthetic=True,pages=1,
      description="Portal listing captured 9 Nov 2026, last fed 16 Apr 2026: still freehold offers £700,000, size '2,700 sq ft' (unlabelled), parking 1 per floor, lower ground floor still advertised to let at £9,400 pa."),
 dict(doc_id="syn-kv-parking",file="synthetic/kelso-villa_parking-allocation-schedule_2026-10.pdf",development=K,unit=f"{K}:whole",doc_type="parking_allocation_schedule",issuer="Abbeygate Estate Management Ltd (fictional)",issuer_role="managing_agent",date="2026-10-06",date_source="printed",authority_tier=3,synthetic=True,pages=1,
      description="Managing agent's parking schedule (Issue 4): 5 allocated spaces; bay 6 reclassified as bin store/turning area after a fire risk assessment."),
 dict(doc_id="syn-shc-finishes",file="synthetic/st-huberts-close_schedule-of-finishes_chiltern-vale_2026-09.pdf",development=S,unit=f"{S}:development (+ house types A–E, plot 59 = type E)",doc_type="schedule_of_finishes",issuer="Chiltern Vale Developments Ltd (fictional)",issuer_role="developer",date="2026-09-15",date_source="printed",authority_tier=3,synthetic=True,pages=2,
      description="Development-wide schedule of finishes, Rev C: 'All en-suites are fitted with walk-in showers… No en-suite has a bath' (p1); house-type table and plot schedule with No. 59 = type E 'The Hedgerley', 5 bed, 2,848 sq ft GIA; type C 'The Denham' 4 bed 2,098 sq ft (p2)."),
 dict(doc_id="syn-shc59-price",file="synthetic/59-st-huberts-close_price-change-instruction_2026-11.pdf",development=S,unit=f"{S}:no-59",doc_type="developer_instruction",issuer="Harcourt Lane LLP for the vendors (fictional)",issuer_role="conveyancer",date="2026-11-03",date_source="printed",authority_tier=4,synthetic=True,pages=1,
      description="Formal vendor instruction to the agent: guide price reduced from £1,458,000 to £1,395,000, effective 9 Nov 2026; asks for particulars and portals to be updated."),
 dict(doc_id="syn-shc59-epc",file="synthetic/59-st-huberts-close_epc-domestic_2025-06.pdf",development=S,unit=f"{S}:no-59",doc_type="epc_certificate",issuer="EPC register (fictional assessor)",issuer_role="official_register",date="2025-06-13",date_source="register",register_date="2026-11-10",authority_tier=2,synthetic=True,pages=1,
      description="Domestic EPC for No. 59: band D (64), potential C (78), total floor area 241 m2 (heated area; excludes the garage)."),
]
for d in docs:
    p=d["file"]; d["sha256"]=hashlib.sha256(open(p,"rb").read()).hexdigest()
    d["page_count"]=int([l for l in subprocess.run(["pdfinfo",p],capture_output=True,text=True).stdout.splitlines() if l.startswith("Pages")][0].split()[-1])
    d.pop("pages",None)
    if d["synthetic"]: d["has_text_layer"]=True
    d.setdefault("supersedes_doc_id",None); d.setdefault("register_date",None)

A,O,SV,EP,TI,LI,PK="carterjonas-98889981","carterjonas-f8692efa","syn-kv-survey","syn-kv-epc","syn-kv-title","syn-kv-listing","syn-kv-parking"
B59,B4,FIN,PR,E59="struttparker-a45c02cc","struttparker-92092382","syn-shc-finishes","syn-shc59-price","syn-shc59-epc"
def ev(doc,page,value,quote,**kw): return dict(doc_id=doc,page=page,value=value,quote=quote,**kw)
C=[
 dict(id="C01",unit=f"{K}:whole",field="price",qualifier={"price_type":"freehold_offers/guide"},type="version_supersession",real_only=True,
  evidence=[ev(A,2,"£700,000 (freehold offers)","Alternatively Freehold offers will be considered at £700,000"),ev(O,2,"£600,000 (guide)","£600,000 Guide Price")],
  expected_resolution="Same issuer (Carter Jonas) and doc type; October 2026 is the candidate. Price is material, so a human confirms. April stays in history as superseded.",
  voice_agent="Pending: don't quote a price. 'The latest particulars show a lower figure than earlier marketing; an agent will confirm the current price.' After sign-off: '£600,000 guide price.'"),
 dict(id="C02",unit=f"{K}:whole",field="price",qualifier={"price_type":"freehold_offers/guide"},type="stale_listing",
  evidence=[ev(LI,1,"£700,000","Freehold offers in excess of £700,000"),ev(O,2,"£600,000","£600,000 Guide Price")],
  expected_resolution="The latest verified document (October particulars, then C01 sign-off) wins. Flag the PropNest listing PNC-7731804 for update and notify the agent.",
  voice_agent="Quote the verified document price; if asked about the listing, say the online listing appears out of date."),
 dict(id="C03",unit=f"{K}:whole",field="floor_area",qualifier={"basis":"unspecified vs NIA/GIA","scope":"whole"},type="unit_or_measurement_mismatch",real_only=True,
  evidence=[ev(A,2,"185 sq m beside 2,700 sq ft in one row","Total (ALL FLOORS) 185 2,700",doc_error=True),ev(O,1,"1,990 sq ft (185 m2) NIA; 2,700 sq ft GIA","1,990 sq ft (185m2) net offices (2,700 sq ft GIA)")],
  expected_resolution="185 sq m = 1,991 sq ft, not 2,700: flag a document error on the April row (not two different areas). Normalise and label: 185 m2 is NIA, 2,700 sq ft is GIA. Prefer October, which states both consistently.",
  voice_agent="Never give a single unlabelled area. Once verified: net and gross separately, each with its basis."),
 dict(id="C04",unit=f"{K}:whole",field="floor_area",qualifier={"basis":"NIA","scope":"whole"},type="true_conflict",
  evidence=[ev(O,1,"1,990 sq ft / 185 m2 NIA","1,990 sq ft (185m2) net offices"),ev(O,2,"185 m2 / 1,990 sq ft NIA","Property NIA … Total 185 1,990"),ev(SV,1,"1,912 sq ft / 177.6 m2 NIA","Total (all floors) 177.6 1,912")],
  expected_resolution="Same unit, field and basis; values can't both be right. The survey (tier 3, basis stated, RICS) outranks the brochure (tier 5) as a candidate, but area is material and this overrides marketing, so a human signs off. The survey's own note explains the difference (second-floor eaves and plant excluded).",
  voice_agent="Conflicting: don't quote a net area. 'The measured survey and the brochure give different net areas; an agent will confirm.'"),
 dict(id="C05",unit=f"{K}:whole",field="floor_area",qualifier={"basis":"GIA","scope":"whole"},type="true_conflict",
  evidence=[ev(O,1,"2,700 sq ft GIA","(2,700 sq ft GIA)"),ev(SV,1,"2,672 sq ft / 248.2 m2 GIA","Total (all floors) … 248.2 2,672")],
  expected_resolution="Small (1%) but real difference on the same basis. Survey is the tier-3 candidate; human confirms (material field). Could be treated as rounding if the team sets a tolerance.",
  voice_agent="Pending: don't quote a gross area until verified."),
 dict(id="C06",unit=f"{K}:lower-ground",field="floor_area",qualifier={"basis":"unspecified vs NIA","scope":"floor:lower_ground"},type="unit_or_measurement_mismatch",
  evidence=[ev(A,1,"468 sq ft (43.45 sq m), basis not printed","468 Sq Ft (43.45 Sq M)"),ev(A,2,"43.45 sq m / 468 sq ft","Lower Floor 43.45 468"),ev(SV,1,"461 sq ft / 42.8 m2 NIA","Lower Ground Floor 42.8 461")],
  expected_resolution="Brochure basis is unspecified, survey is NIA, so they are not directly comparable. Keep both, labelled; the survey's NIA is the candidate for an NIA fact. Never default the brochure figure to NIA.",
  voice_agent="Give the area with its basis ('about 461 sq ft net internal, per the measured survey') once verified."),
 dict(id="C07",unit=f"{K}:whole",field="floor_area",qualifier={"basis":"EPC vs NIA/GIA","scope":"whole"},type="unit_or_measurement_mismatch",
  evidence=[ev(EP,1,"239 m2 (EPC total useful floor area)","Total useful floor area 239 square metres"),ev(SV,1,"248.2 m2 GIA; 177.6 m2 NIA","Total (all floors) 177.6 1,912 248.2 2,672")],
  expected_resolution="Different bases: not a conflict. Store the EPC area with basis=EPC; never compare it with NIA or GIA.",
  voice_agent="If asked, the EPC area is quoted only as 'the EPC records 239 square metres'."),
 dict(id="C08",unit=f"{K}:whole",field="epc_rating",qualifier={},type="official_record_mismatch",
  evidence=[ev(A,2,"B","EPC has been assessed as B."),ev(O,2,"B","EPC has been assessed as B."),ev(LI,1,"B","EPC B"),ev(EP,1,"C (58)","This property’s current energy rating is C.")],
  expected_resolution="Marketing says B; the register certificate (2 Sept 2026, tier 2) says C. Do not auto-correct; a human checks the register and whether a newer certificate exists. Tier 2 is the candidate.",
  voice_agent="Don't assert either. 'The official EPC record and the marketing disagree; an agent will confirm the rating.'"),
 dict(id="C09",unit=f"{K}:whole",field="parking",qualifier={"scope":"total"},type="true_conflict",
  evidence=[ev(O,1,"6 spaces total","Parking on site (6 spaces total)"),ev(A,2,"six spaces","Six parking spaces are with the building"),ev(SV,1,"6 marked bays","Six (6) marked parking bays"),ev(TI,1,"six spaces numbered 1 to 6","comprising six parking spaces numbered 1 to 6"),ev(PK,1,"5 allocated (bay 6 reclassified)","Total allocated parking spaces: 5 (five)")],
  expected_resolution="Survey and allocation schedule are tier-3 peers and the title (tier 2) still shows 6, but the schedule is later and explains bay 6's loss to fire access. Can't both be right as 'usable spaces': do not auto-pick. Human sign-off; record who, when, why.",
  voice_agent="Conflicting: 'Sources disagree on the number of parking spaces; an agent will confirm.' Capture the lead."),
 dict(id="C10",unit=f"{K}:whole vs per-floor",field="parking",qualifier={"scope":"per_floor vs total"},type="scope_difference",real_only=True,
  evidence=[ev(A,1,"1 space per floor","Parking on site (one space per floor)"),ev(A,2,"1 per floor on any letting; 6 with the building","Six parking spaces are with the building and one space is available per floor on any letting"),ev(O,1,"6 total","Parking on site (6 spaces total)")],
  expected_resolution="Not a conflict: per-floor-letting allowance and whole-building total are different scopes. Keep both at their stated scope.",
  voice_agent="'Each floor let comes with one space; the building as a whole has (verified total) spaces.'"),
 dict(id="C11",unit=f"{K}:lower-ground",field="availability",qualifier={},type="official_record_mismatch",
  evidence=[ev(A,1,"lower ground floor to let","TO LET—LOWER GROUND FLOOR"),ev(LI,1,"lower ground floor currently available","The lower ground floor (468 sq ft) is currently available."),ev(TI,1,"leased for 10 years from 1 Sept 2026","NOTICE of a lease dated 1 September 2026 of the lower ground floor"),ev(O,1,"one floor remaining","For Sale or To Let (one floor remaining)")],
  expected_resolution="Title (tier 2) shows the LG floor let from 1 Sept 2026; marketing still offers it. Do not auto-correct; human confirms against the current title and lease. Flag the listing.",
  voice_agent="'The lower ground floor appears to have been let; an agent will confirm what's still available.'"),
 dict(id="C12",unit=f"{S}:no-59",field="price",qualifier={"price_type":"guide"},type="version_supersession",
  evidence=[ev(B59,2,"£1,458,000 guide","Guide price £1,458,000"),ev(PR,1,"£1,395,000 guide from 9 Nov 2026","Revised £1,395,000 09/11/2026")],
  expected_resolution="Later, higher-tier formal instruction (tier 4, 3 Nov 2026) supersedes the April 2026 brochure (tier 5). Candidate £1,395,000; price is material, so a human confirms. Brochure needs reissue.",
  voice_agent="Pending: don't quote. After sign-off: 'The guide price is £1,395,000.'"),
 dict(id="C13",unit=f"{S}:no-59 vs {S}:development",field="bathrooms / en_suite_fittings",qualifier={"scope":"development vs unit"},type="scope_difference",
  evidence=[ev(FIN,1,"All en-suites walk-in showers, no en-suite baths (development scope)","All en-suites are fitted with walk-in showers… No en-suite has a bath."),ev(B59,2,"principal en suite BATHROOM; guest en suite shower room (unit scope)","a fully fitted en suite bathroom. The guest suite benefits from an en suite shower room",note="text Caesar-shifted +29 in the PDF; decode first")],
  expected_resolution="Do not copy the development-wide claim onto No. 59. Keep both at stated scope; the unit-level brochure is the only unit source. The schedule itself warns finishes may have been altered.",
  voice_agent="'For No. 59 specifically, the particulars describe an en-suite bathroom to the principal bedroom and a shower room to the guest suite.' Don't say 'all en-suites have showers'."),
 dict(id="C14",unit=f"{S}:no-59",field="floor_area",qualifier={"basis":"unspecified vs EPC","scope":"whole"},type="unit_or_measurement_mismatch",
  evidence=[ev(B59,2,"2,848 sq ft (264.6 sq m), basis not printed","2,848 sq ft (264.6 sq m)"),ev(E59,1,"241 m2 (EPC heated area, excludes garage)","Total floor area 241 square metres"),ev(FIN,2,"type E 2,848 sq ft GIA","E The Hedgerley 5 3 5 Double 2,848")],
  expected_resolution="Different bases (brochure likely GIA incl. garage per the type table; EPC is heated area). Not a conflict; normalise and label. 2,848 sq ft = 264.6 m2 checks arithmetically.",
  voice_agent="Give the area with its basis; never a single unlabelled figure."),
 dict(id="C15",unit=f"{S}:no-59 vs {S}:4-bed-unnumbered",field="epc_rating",qualifier={},type="plot_or_type_variation",
  evidence=[ev(B4,4,"C (4-bed, different house)","EPC Rating: C"),ev(E59,1,"D (No. 59)","This property’s current energy rating is D.")],
  expected_resolution="Resolve entities first: the 4-bed brochure (type C, 2,098 sq ft) is a different house from No. 59 (type E, 2,848 sq ft). Never merge. No. 59's EPC is D (single tier-2 source); C belongs only to the 4-bed.",
  voice_agent="For No. 59: 'The EPC rating is D.' Never answer with the other house's C."),
]
TYPES=["true_conflict","version_supersession","unit_or_measurement_mismatch","scope_difference","plot_or_type_variation","stale_listing","official_record_mismatch"]
assert set(TYPES)<=set(c["type"] for c in C)
for c in C: c["real_only"]=c.get("real_only",False); c["requires_human"]=c["type"] in ("true_conflict","official_record_mismatch","version_supersession") or c["field"] in ("price","floor_area")
agreements=[
 dict(unit=f"{K}:whole",field="tenure",value="freehold",evidence=[A,O,TI,LI],note="All agree; the title (tier 2) verifies it."),
 dict(unit=f"{K}:whole",field="listed_status",value="Grade II listed",evidence=[A,O]),
 dict(unit=f"{K}:lower-ground",field="rent",value="£9,400 pa exclusive (per floor)",evidence=[A,LI],note="Single brochure source; may be moot if the LG lease (C11) is confirmed."),
 dict(unit=f"{S}:4-bed-unnumbered",field="tenure",value="freehold",evidence=[B4]),
]
json.dump(dict(generated="2026-11-12",note="Synthetic documents are fictional; every synthetic PDF carries 'synthetic: true' in its Subject/Keywords metadata.",documents=docs),open("manifest.json","w"),indent=2,ensure_ascii=False)
json.dump(dict(contradictions=C,agreements=agreements),open("contradictions.json","w"),indent=2,ensure_ascii=False)
name={d["doc_id"]:d["file"].split("/")[-1] for d in docs}
L=["# sample_data: demo documents and planted contradictions","","Two developments: **Kelso Villa, Upper Bristol Road, Bath BA1 3AU** (Grade II offices, Carter Jonas) and **St Huberts Close, Gerrards Cross** (Strutt & Parker).","","- `real/`: the four real brochures (Kelso PDFs are scanned images with no text layer: use OCR/vision).","- `synthetic/`: fictional documents generated by `generate_synthetic.py` (reportlab). Every one has `synthetic: true` in its PDF Subject/Keywords and a small 'Demo document' footer. All people, firms, title and certificate numbers are invented.","- `previews/`: page 1 of each synthetic PDF as PNG.","- `manifest.json`: every document with development, unit, doc_type, issuer, date, authority tier, synthetic flag, page count and sha256.","- `contradictions.json`: the answer key (each contradiction with evidence doc/page/quote, type, expected resolution, voice-agent line) plus fields that agree.","","Rebuild: `python3 generate_synthetic.py && python3 build_manifest.py`","","## Documents","","| doc_id | file | type | tier | issuer | date | synthetic | what it says |","|---|---|---|---|---|---|---|---|"]
for d in docs: L.append(f"| {d['doc_id']} | `{d['file']}` | {d['doc_type']} | {d['authority_tier']} | {d['issuer']} | {d['date']} | {'yes' if d['synthetic'] else 'no'} | {d['description']} |")
L+=["","## Contradictions (answer key)","","| id | unit | field | type | documents (page) | values | expected resolution |","|---|---|---|---|---|---|---|"]
for c in C:
    L.append(f"| {c['id']} | {c['unit'].replace(K+':','kelso:').replace(S+':','shc:')} | {c['field']} {json.dumps(c['qualifier']) if c['qualifier'] else ''} | {c['type']}{' (real docs only)' if c['real_only'] else ''} | "+"; ".join(f"{e['doc_id']} p{e['page']}" for e in c["evidence"])+" | "+"; ".join(e["value"] for e in c["evidence"])+f" | {c['expected_resolution']} |")
L+=["","## What the voice agent should say","",*[f"- **{c['id']}** ({c['type']}): {c['voice_agent']}" for c in C],"","## Fields that agree (should verify cleanly)","",*[f"- {a['unit']}: {a['field']} = {a['value']} ({', '.join(a['evidence'])}){' . '+a['note'] if a.get('note') else ''}" for a in agreements],"","## Caveats","","- Kelso brochure dates (April / October 2026) come from the spec; neither PDF prints a date (`date_source: manual`).","- The No. 59 brochure prints 'Particulars prepared April' without a year in decodable text; 2026 comes from the file metadata (created 6 May 2026). Parts of its text layer are Caesar-shifted by +29 (broken font encoding).","- `parking_allocation_schedule` isn't in the schema's doc_type list yet; it's treated as tier 3 here (the spec names allocation schedules as authoritative for parking). Add it to the enum.","- C04/C05 are 'true conflicts' across tiers (survey vs brochure); the higher tier is the candidate but a human must sign off because area is material."]
open("README.md","w").write("\n".join(L)+"\n")
print(len(docs),"docs",len(C),"contradictions")
