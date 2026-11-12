# sample_data

Demo documents for the verified fact record, at most three per development (real brochures included). Synthetic PDFs are fictional (people, firms, reference numbers) and carry `synthetic: true` in their PDF Subject/Keywords plus a small 'Demo document' footer.

- `kelso-villa/`: 2 real Carter Jonas brochures (scanned, no text layer: needs OCR/vision) + synthetic measured survey + preview PNG + `contradictions.md`.
- `st-huberts-close/`: real No. 59 Strutt & Parker brochure + synthetic price-change instruction + synthetic schedule of finishes + previews + `contradictions.md`.
- `manifest.json`: every document with development, unit, doc_type, issuer, date, authority tier, synthetic flag, pages, sha256.
- `contradictions.json`: answer key with evidence (doc, page, value, verbatim quote), type, expected resolution, voice-agent line, plus types covered/not covered.
- Rebuild: `python3 generate_synthetic.py && python3 build_manifest.py`

## Documents

| file | type | tier | issuer | date | what it says |
|---|---|---|---|---|---|
| `kelso-villa/real_kelso-villa_april-2026_to-let_carterjonas-98889981.pdf` | particulars | 5 | Carter Jonas | 2026-04 | Real To Let (lower ground floor) particulars: 468 sq ft (43.45 sq m), £9,400 pa per floor, one parking space per floor, freehold offers £700,000, EPC B; 'Total (ALL FLOORS) 185 | 2,700' row error. |
| `kelso-villa/real_kelso-villa_october-2026_for-sale_carterjonas-f8692efa.pdf` | particulars | 5 | Carter Jonas | 2026-10 | Real For Sale particulars: 1,990 sq ft (185 m2) net, 2,700 sq ft GIA, £600,000 guide, 6 parking spaces total, EPC B. |
| `kelso-villa/synthetic_kelso-villa_measured-survey_holloway-reid_2026-09.pdf` | measured_survey | 3 | Holloway & Reid (fictional) | 2026-09-18 | Synthetic 4-page measured survey: schedule of areas and notes (p1), floor plans LG/G (p2) and 1st/2nd (p3), courtyard site plan (p4). NIA 177.6 m2 / 1,912 sq ft; GIA 248.2 m2 / 2,672 sq ft; LG 461 sq ft NIA; 5 allocated bays, bay 6 bin store and turning area; note cites current EPC band C (cert 9417-3082-6651-2049-7735, 2 Sep 2026). |
| `st-huberts-close/real_59-st-huberts-close_5bed_struttparker-a45c02cc.pdf` | particulars | 5 | Strutt & Parker | 2026-04 | Real brochure for No. 59: 5 bed, principal en suite bathroom + guest en suite shower room, 2,848 sq ft (264.6 sq m), guide £1,458,000. Parts of the text layer are Caesar-shifted +29. |
| `st-huberts-close/synthetic_59-st-huberts-close_price-change-instruction_2026-11.pdf` | developer_instruction | 4 | Harcourt Lane LLP for the vendors (fictional) | 2026-11-03 | Synthetic formal vendor instruction: guide price £1,458,000 to £1,395,000, effective 9 Nov 2026. |
| `st-huberts-close/synthetic_st-huberts-close_schedule-of-finishes_chiltern-vale_2026-09.pdf` | schedule_of_finishes | 3 | Chiltern Vale Developments Ltd (fictional) | 2026-09-15 | Synthetic development-wide schedule of finishes Rev C: 'All en-suites are fitted with walk-in showers' (p1); house types and plot schedule (p2): No. 59 = type E 5-bed standard spec; plots 53/57 = type D 4-bed with principal en-suite bath. |

## Contradictions

| id | unit | field | type | sources (page) | values | expected resolution | voice agent says |
|---|---|---|---|---|---|---|---|
| C01 | whole | price | version_supersession (real docs only) | carterjonas-98889981 p2; carterjonas-f8692efa p2 | £700,000 freehold offers; £600,000 guide | Same issuer and doc type: October 2026 is the candidate. Price is material, so a human confirms. April kept in history as superseded. | Pending: don't quote a price; say the latest particulars show a change and an agent will confirm. After sign-off: '£600,000 guide price.' |
| C02 | whole | floor_area | unit_or_measurement_mismatch (real docs only) | carterjonas-98889981 p2; carterjonas-f8692efa p1 | 185 sq m beside 2,700 sq ft in one row; 1,990 sq ft (185 m2) net; 2,700 sq ft GIA | 185 sq m = 1,991 sq ft, not 2,700: flag a document error on the April row, not two areas. Label 185 m2 as NIA and 2,700 sq ft as GIA; prefer October. | Never give a single unlabelled area; once verified give net and gross separately. |
| C03 | whole | floor_area | true_conflict | carterjonas-f8692efa p1; syn-kv-survey p1 | 1,990 sq ft / 185 m2 NIA; 1,912 sq ft / 177.6 m2 NIA | Same unit, field and basis; can't both be right. Survey (tier 3, RICS basis stated) is the candidate over the brochure (tier 5), but area is material: human sign-off. Survey note explains the gap (2nd-floor eaves and plant excluded). | Conflicting: don't quote a net area; say the survey and the brochure differ and an agent will confirm. |
| C04 | whole | floor_area | true_conflict | carterjonas-f8692efa p1; syn-kv-survey p1 | 2,700 sq ft GIA; 2,672 sq ft / 248.2 m2 GIA | Same basis, about 1% apart. Survey is the candidate; human confirms (or the team sets a rounding tolerance). | Pending: don't quote a gross area until verified. |
| C05 | lower-ground | floor_area | unit_or_measurement_mismatch | carterjonas-98889981 p1; syn-kv-survey p1 | 468 sq ft (43.45 sq m), basis not printed; 461 sq ft / 42.8 m2 NIA | Different (unstated vs NIA) bases, so not directly comparable. Keep both labelled; never default the brochure figure to NIA. Survey NIA is the candidate NIA fact. | Give the area with its basis once verified, e.g. 'about 461 sq ft net internal, per the measured survey'. |
| C06 | whole | parking | true_conflict | carterjonas-f8692efa p1; carterjonas-98889981 p2; syn-kv-survey p1; syn-kv-survey p4 | 6 spaces total; six spaces; 5 allocated; bay 6 bin store and turning area; 5 allocated | Survey (tier 3, dated 9 Sep 2026) says 5 usable bays; both brochures say 6. Don't auto-pick: human sign-off with who, when, why. Loser kept in history. | Conflicting: say sources disagree on the number of spaces and an agent will confirm; capture the lead. |
| C07 | whole vs per-floor | parking | scope_difference (real docs only) | carterjonas-98889981 p1; carterjonas-f8692efa p1 | 1 space per floor; 6 total | Not a conflict: per-floor letting allowance vs whole-building total. Keep both at their stated scope. | 'Each floor let comes with one space; the building total is being confirmed.' |
| C08 | whole | epc_rating | official_record_mismatch | carterjonas-98889981 p2; carterjonas-f8692efa p2; syn-kv-survey p1 | B; B; C (cites register cert 9417-3082-6651-2049-7735, 2 Sep 2026) | Marketing says B; the survey cites the current register certificate as C. Don't auto-correct: a human checks the EPC register itself. | Don't assert either; say the official EPC record and the marketing appear to disagree and an agent will confirm. |
| C09 | no-59 | price | version_supersession | struttparker-a45c02cc p2; syn-shc59-price p1 | £1,458,000 guide; £1,395,000 from 9 Nov 2026 | Later formal instruction (tier 4, 3 Nov 2026) supersedes the April 2026 brochure (tier 5). Candidate £1,395,000; price is material so a human confirms. | Pending: don't quote. After sign-off: 'The guide price is £1,395,000.' |
| C10 | no-59 vs development | en_suite_fittings | scope_difference | syn-shc-finishes p1; struttparker-a45c02cc p2 | all en-suites walk-in showers (development scope); principal en suite BATHROOM; guest en suite shower room (unit scope) | Never copy the development-wide claim onto No. 59. Keep both at stated scope; the brochure is the only unit-level source. | For No. 59 say the particulars describe an en-suite bathroom to the principal bedroom and a shower room to the guest suite; don't say 'all en-suites have showers'. |
| C11 | no-59 (type E) vs plots 53/57 (type D) | en_suite_fittings / bedrooms | plot_or_type_variation | syn-shc-finishes p2; syn-shc-finishes p2 | No. 59 = type E, 5 bed, standard spec; type D = 4 bed, principal en-suite with freestanding bath | Resolve the entity first: No. 59 is type E. Never merge type D facts (4 bed, en-suite bath) into No. 59. | Answer only for No. 59; if the caller names another plot, treat it as a different property. |

**Types covered (6/7):** official_record_mismatch, plot_or_type_variation, scope_difference, true_conflict, unit_or_measurement_mismatch, version_supersession.  
**Not covered:** stale_listing (needs a portal listing or CRM row, which the three-document limit leaves out).

## Caveats

- Kelso brochure dates come from the spec, not the PDFs.
- C08 rests on the survey quoting the EPC register (secondary evidence), not on a register extract.
- The No. 59 brochure's C10 quote sits in Caesar-shifted (+29) text, so it only matches after decoding.
- Kelso quotes can only be checked after OCR (scanned PDFs).
