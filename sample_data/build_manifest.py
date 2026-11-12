import json, hashlib, subprocess, re, os
K="kelso-villa-ba1-3au"; S="st-huberts-close-gerrards-cross"
KD,SD="kelso-villa/","st-huberts-close/"
docs=[
 dict(doc_id="carterjonas-98889981",file=KD+"real_kelso-villa_april-2026_to-let_carterjonas-98889981.pdf",development=K,unit=f"{K}:whole (+ :lower-ground)",doc_type="particulars",issuer="Carter Jonas",date="2026-04",date_source="manual (from spec; not printed)",authority_tier=5,synthetic=False,version_label="april_2026",has_text_layer=False,
      description="Real To Let (lower ground floor) particulars: 468 sq ft (43.45 sq m), £9,400 pa per floor, one parking space per floor, freehold offers £700,000, EPC B; 'Total (ALL FLOORS) 185 | 2,700' row error."),
 dict(doc_id="carterjonas-f8692efa",file=KD+"real_kelso-villa_october-2026_for-sale_carterjonas-f8692efa.pdf",development=K,unit=f"{K}:whole",doc_type="particulars",issuer="Carter Jonas",date="2026-10",date_source="manual (from spec; not printed)",authority_tier=5,synthetic=False,version_label="october_2026",supersedes_doc_id="carterjonas-98889981",has_text_layer=False,
      description="Real For Sale particulars: 1,990 sq ft (185 m2) net, 2,700 sq ft GIA, £600,000 guide, 6 parking spaces total, EPC B."),
 dict(doc_id="syn-kv-survey",file=KD+"synthetic_kelso-villa_measured-survey_holloway-reid_2026-09.pdf",development=K,unit=f"{K}:whole + floors",doc_type="measured_survey",issuer="Holloway & Reid (fictional)",date="2026-09-18",date_source="printed",authority_tier=3,synthetic=True,has_text_layer=True,
      description="Synthetic 4-page measured survey: schedule of areas and notes (p1), floor plans LG/G (p2) and 1st/2nd (p3), courtyard site plan (p4). NIA 177.6 m2 / 1,912 sq ft; GIA 248.2 m2 / 2,672 sq ft; LG 461 sq ft NIA; 5 allocated bays, bay 6 bin store and turning area; note cites current EPC band C (cert 9417-3082-6651-2049-7735, 2 Sep 2026)."),
 dict(doc_id="struttparker-a45c02cc",file=SD+"real_59-st-huberts-close_5bed_struttparker-a45c02cc.pdf",development=S,unit=f"{S}:no-59",doc_type="particulars",issuer="Strutt & Parker",date="2026-04",date_source="printed month ('Particulars prepared April'); year from file metadata",authority_tier=5,synthetic=False,has_text_layer=True,
      description="Real brochure for No. 59: 5 bed, principal en suite bathroom + guest en suite shower room, 2,848 sq ft (264.6 sq m), guide £1,458,000. Parts of the text layer are Caesar-shifted +29."),
 dict(doc_id="syn-shc59-price",file=SD+"synthetic_59-st-huberts-close_price-change-instruction_2026-11.pdf",development=S,unit=f"{S}:no-59",doc_type="developer_instruction",issuer="Harcourt Lane LLP for the vendors (fictional)",date="2026-11-03",date_source="printed",authority_tier=4,synthetic=True,has_text_layer=True,
      description="Synthetic formal vendor instruction: guide price £1,458,000 to £1,395,000, effective 9 Nov 2026."),
 dict(doc_id="syn-shc-finishes",file=SD+"synthetic_st-huberts-close_schedule-of-finishes_chiltern-vale_2026-09.pdf",development=S,unit=f"{S}:development (+ house types, plots)",doc_type="schedule_of_finishes",issuer="Chiltern Vale Developments Ltd (fictional)",date="2026-09-15",date_source="printed",authority_tier=3,synthetic=True,has_text_layer=True,
      description="Synthetic development-wide schedule of finishes Rev C: 'All en-suites are fitted with walk-in showers' (p1); house types and plot schedule (p2): No. 59 = type E 5-bed standard spec; plots 53/57 = type D 4-bed with principal en-suite bath."),
]
for d in docs:
    d["sha256"]=hashlib.sha256(open(d["file"],"rb").read()).hexdigest()
    d["page_count"]=int(re.search(r"Pages:\s+(\d+)",subprocess.run(["pdfinfo",d["file"]],capture_output=True,text=True).stdout).group(1))
    d.setdefault("supersedes_doc_id",None)
A,O,SV,B59,PR,FIN="carterjonas-98889981","carterjonas-f8692efa","syn-kv-survey","struttparker-a45c02cc","syn-shc59-price","syn-shc-finishes"
def ev(doc,page,value,quote,**kw): return dict(doc_id=doc,page=page,value=value,quote=quote,**kw)
C=[
 dict(id="C01",development=K,unit=f"{K}:whole",field="price",qualifier={},type="version_supersession",real_only=True,
  evidence=[ev(A,2,"£700,000 freehold offers","Alternatively Freehold offers will be considered at £700,000"),ev(O,2,"£600,000 guide","£600,000 Guide Price")],
  expected_resolution="Same issuer and doc type: October 2026 is the candidate. Price is material, so a human confirms. April kept in history as superseded.",
  voice_agent="Pending: don't quote a price; say the latest particulars show a change and an agent will confirm. After sign-off: '£600,000 guide price.'"),
 dict(id="C02",development=K,unit=f"{K}:whole",field="floor_area",qualifier={"basis":"unspecified vs NIA/GIA","scope":"whole"},type="unit_or_measurement_mismatch",real_only=True,
  evidence=[ev(A,2,"185 sq m beside 2,700 sq ft in one row","Total (ALL FLOORS) 185 2,700",doc_error=True),ev(O,1,"1,990 sq ft (185 m2) net; 2,700 sq ft GIA","1,990 sq ft (185m2) net offices (2,700 sq ft GIA)")],
  expected_resolution="185 sq m = 1,991 sq ft, not 2,700: flag a document error on the April row, not two areas. Label 185 m2 as NIA and 2,700 sq ft as GIA; prefer October.",
  voice_agent="Never give a single unlabelled area; once verified give net and gross separately."),
 dict(id="C03",development=K,unit=f"{K}:whole",field="floor_area",qualifier={"basis":"NIA","scope":"whole"},type="true_conflict",
  evidence=[ev(O,1,"1,990 sq ft / 185 m2 NIA","1,990 sq ft (185m2) net offices"),ev(SV,1,"1,912 sq ft / 177.6 m2 NIA","Total (all floors) 177.6 1,912")],
  expected_resolution="Same unit, field and basis; can't both be right. Survey (tier 3, RICS basis stated) is the candidate over the brochure (tier 5), but area is material: human sign-off. Survey note explains the gap (2nd-floor eaves and plant excluded).",
  voice_agent="Conflicting: don't quote a net area; say the survey and the brochure differ and an agent will confirm."),
 dict(id="C04",development=K,unit=f"{K}:whole",field="floor_area",qualifier={"basis":"GIA","scope":"whole"},type="true_conflict",
  evidence=[ev(O,1,"2,700 sq ft GIA","(2,700 sq ft GIA)"),ev(SV,1,"2,672 sq ft / 248.2 m2 GIA","248.2 2,672")],
  expected_resolution="Same basis, about 1% apart. Survey is the candidate; human confirms (or the team sets a rounding tolerance).",
  voice_agent="Pending: don't quote a gross area until verified."),
 dict(id="C05",development=K,unit=f"{K}:lower-ground",field="floor_area",qualifier={"basis":"unspecified vs NIA","scope":"floor:lower_ground"},type="unit_or_measurement_mismatch",
  evidence=[ev(A,1,"468 sq ft (43.45 sq m), basis not printed","468 Sq Ft (43.45 Sq M)"),ev(SV,1,"461 sq ft / 42.8 m2 NIA","Lower Ground Floor 42.8 461")],
  expected_resolution="Different (unstated vs NIA) bases, so not directly comparable. Keep both labelled; never default the brochure figure to NIA. Survey NIA is the candidate NIA fact.",
  voice_agent="Give the area with its basis once verified, e.g. 'about 461 sq ft net internal, per the measured survey'."),
 dict(id="C06",development=K,unit=f"{K}:whole",field="parking",qualifier={"scope":"total"},type="true_conflict",
  evidence=[ev(O,1,"6 spaces total","Parking on site (6 spaces total)"),ev(A,2,"six spaces","Six parking spaces are with the building"),ev(SV,1,"5 allocated; bay 6 bin store and turning area","five (5) bays (1 to 5) were in use as allocated parking"),ev(SV,4,"5 allocated","Allocated parking bays: 5")],
  expected_resolution="Survey (tier 3, dated 9 Sep 2026) says 5 usable bays; both brochures say 6. Don't auto-pick: human sign-off with who, when, why. Loser kept in history.",
  voice_agent="Conflicting: say sources disagree on the number of spaces and an agent will confirm; capture the lead."),
 dict(id="C07",development=K,unit=f"{K}:whole vs per-floor",field="parking",qualifier={"scope":"per_floor vs total"},type="scope_difference",real_only=True,
  evidence=[ev(A,1,"1 space per floor","Parking on site (one space per floor)"),ev(O,1,"6 total","Parking on site (6 spaces total)")],
  expected_resolution="Not a conflict: per-floor letting allowance vs whole-building total. Keep both at their stated scope.",
  voice_agent="'Each floor let comes with one space; the building total is being confirmed.'"),
 dict(id="C08",development=K,unit=f"{K}:whole",field="epc_rating",qualifier={},type="official_record_mismatch",
  evidence=[ev(A,2,"B","EPC has been assessed as B."),ev(O,2,"B","EPC has been assessed as B."),ev(SV,1,"C (cites register cert 9417-3082-6651-2049-7735, 2 Sep 2026)","band C",note="secondary reference to the official register, quoted in a tier-3 survey")],
  expected_resolution="Marketing says B; the survey cites the current register certificate as C. Don't auto-correct: a human checks the EPC register itself.",
  voice_agent="Don't assert either; say the official EPC record and the marketing appear to disagree and an agent will confirm."),
 dict(id="C09",development=S,unit=f"{S}:no-59",field="price",qualifier={"price_type":"guide"},type="version_supersession",
  evidence=[ev(B59,2,"£1,458,000 guide","Guide price £1,458,000"),ev(PR,1,"£1,395,000 from 9 Nov 2026","Revised £1,395,000 09/11/2026")],
  expected_resolution="Later formal instruction (tier 4, 3 Nov 2026) supersedes the April 2026 brochure (tier 5). Candidate £1,395,000; price is material so a human confirms.",
  voice_agent="Pending: don't quote. After sign-off: 'The guide price is £1,395,000.'"),
 dict(id="C10",development=S,unit=f"{S}:no-59 vs development",field="en_suite_fittings",qualifier={"scope":"development vs unit"},type="scope_difference",
  evidence=[ev(FIN,1,"all en-suites walk-in showers (development scope)","All en-suites are fitted with walk-in showers"),ev(B59,2,"principal en suite BATHROOM; guest en suite shower room (unit scope)","fitted en suite bathroom",note="this sentence is Caesar-shifted +29 in the text layer; decode first")],
  expected_resolution="Never copy the development-wide claim onto No. 59. Keep both at stated scope; the brochure is the only unit-level source.",
  voice_agent="For No. 59 say the particulars describe an en-suite bathroom to the principal bedroom and a shower room to the guest suite; don't say 'all en-suites have showers'."),
 dict(id="C11",development=S,unit=f"{S}:no-59 (type E) vs plots 53/57 (type D)",field="en_suite_fittings / bedrooms",qualifier={"scope":"plot/house_type"},type="plot_or_type_variation",
  evidence=[ev(FIN,2,"No. 59 = type E, 5 bed, standard spec","59 E No Standard type E specification"),ev(FIN,2,"type D = 4 bed, principal en-suite with freestanding bath","Type D: principal en-suite with freestanding bath and separate shower")],
  expected_resolution="Resolve the entity first: No. 59 is type E. Never merge type D facts (4 bed, en-suite bath) into No. 59.",
  voice_agent="Answer only for No. 59; if the caller names another plot, treat it as a different property."),
]
TYPES=["true_conflict","version_supersession","unit_or_measurement_mismatch","scope_difference","plot_or_type_variation","stale_listing","official_record_mismatch"]
covered=sorted(set(c["type"] for c in C)); uncovered=[t for t in TYPES if t not in covered]
for c in C: c.setdefault("real_only",False); c["requires_human"]=c["type"] in ("true_conflict","official_record_mismatch","version_supersession") or c["field"] in ("price","floor_area")
agreements=[dict(unit=f"{K}:whole",field="tenure",value="freehold",evidence=[A,O]),dict(unit=f"{K}:whole",field="listed_status",value="Grade II",evidence=[A,O]),
 dict(unit=f"{S}:no-59",field="floor_area",value="2,848 sq ft (brochure, basis unprinted) = type E 2,848 sq ft GIA (schedule)",evidence=[B59,FIN]),dict(unit=f"{S}:no-59",field="bedrooms",value="5",evidence=[B59,FIN])]
# quote check
n=lambda s:re.sub(r"\s+"," ",s.replace("’","'")).strip()
F={d["doc_id"]:d for d in docs}; problems=[]
for c in C:
    for e in c["evidence"]:
        d=F[e["doc_id"]]
        if not d["has_text_layer"]: e["quote_check"]="scanned: verify by OCR/vision"; continue
        t=n(subprocess.run(["pdftotext","-f",str(e["page"]),"-l",str(e["page"]),d["file"],"-"],capture_output=True,text=True).stdout)
        ok=n(e["quote"]) in t; e["quote_check"]="verbatim in pdftotext" if ok else "NOT in pdftotext (see note)"
        if not ok: problems.append((c["id"],e["doc_id"],e["quote"]))
print("quote problems:",problems)
json.dump(dict(generated="2026-11-12",layout="one folder per development; filenames prefixed real_ / synthetic_",documents=docs),open("manifest.json","w"),indent=2,ensure_ascii=False)
json.dump(dict(types_covered=covered,types_not_covered=uncovered,contradictions=C,agreements=agreements),open("contradictions.json","w"),indent=2,ensure_ascii=False)
def table(cs):
    L=["| id | unit | field | type | sources (page) | values | expected resolution | voice agent says |","|---|---|---|---|---|---|---|---|"]
    for c in cs: L.append(f"| {c['id']} | {c['unit'].replace(K+':','').replace(S+':','')} | {c['field']} | {c['type']}{' (real docs only)' if c['real_only'] else ''} | "+"; ".join(f"{e['doc_id']} p{e['page']}" for e in c['evidence'])+" | "+"; ".join(e['value'] for e in c['evidence'])+f" | {c['expected_resolution']} | {c['voice_agent']} |")
    return L
for folder,dev,title in (("kelso-villa",K,"Kelso Villa, Upper Bristol Road, Bath BA1 3AU"),("st-huberts-close",S,"59 St Huberts Close, Gerrards Cross")):
    ds=[d for d in docs if d["development"]==dev]
    L=[f"# {title}: documents and contradictions","","| file | type | tier | issuer | date | real/synthetic |","|---|---|---|---|---|---|"]
    L+=[f"| `{os.path.basename(d['file'])}` | {d['doc_type']} | {d['authority_tier']} | {d['issuer']} | {d['date']} | {'synthetic' if d['synthetic'] else 'real'} |" for d in ds]
    L+=["","## Contradictions",""]+table([c for c in C if c["development"]==dev])
    open(f"{folder}/contradictions.md","w").write("\n".join(L)+"\n")
R=["# sample_data","","Demo documents for the verified fact record, at most three per development (real brochures included). Synthetic PDFs are fictional (people, firms, reference numbers) and carry `synthetic: true` in their PDF Subject/Keywords plus a small 'Demo document' footer.","",
 "- `kelso-villa/`: 2 real Carter Jonas brochures (scanned, no text layer: needs OCR/vision) + synthetic measured survey + preview PNG + `contradictions.md`.",
 "- `st-huberts-close/`: real No. 59 Strutt & Parker brochure + synthetic price-change instruction + synthetic schedule of finishes + previews + `contradictions.md`.",
 "- `manifest.json`: every document with development, unit, doc_type, issuer, date, authority tier, synthetic flag, pages, sha256.",
 "- `contradictions.json`: answer key with evidence (doc, page, value, verbatim quote), type, expected resolution, voice-agent line, plus types covered/not covered.",
 "- Rebuild: `python3 generate_synthetic.py && python3 build_manifest.py`","","## Documents","","| file | type | tier | issuer | date | what it says |","|---|---|---|---|---|---|"]
R+=[f"| `{d['file']}` | {d['doc_type']} | {d['authority_tier']} | {d['issuer']} | {d['date']} | {d['description']} |" for d in docs]
R+=["","## Contradictions",""]+table(C)+["",f"**Types covered ({len(covered)}/7):** {', '.join(covered)}.  ",f"**Not covered:** {', '.join(uncovered) or 'none'} (needs a portal listing or CRM row, which the three-document limit leaves out).","",
 "## Caveats","","- Kelso brochure dates come from the spec, not the PDFs.","- C08 rests on the survey quoting the EPC register (secondary evidence), not on a register extract.","- The No. 59 brochure's C10 quote sits in Caesar-shifted (+29) text, so it only matches after decoding.","- Kelso quotes can only be checked after OCR (scanned PDFs)."]
open("README.md","w").write("\n".join(R)+"\n")
print("covered",covered,"uncovered",uncovered)
