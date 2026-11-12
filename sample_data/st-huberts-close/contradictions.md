# 59 St Huberts Close, Gerrards Cross: documents and contradictions

| file | type | tier | issuer | date | real/synthetic |
|---|---|---|---|---|---|
| `real_59-st-huberts-close_5bed_struttparker-a45c02cc.pdf` | particulars | 5 | Strutt & Parker | 2026-04 | real |
| `synthetic_59-st-huberts-close_price-change-instruction_2026-11.pdf` | developer_instruction | 4 | Harcourt Lane LLP for the vendors (fictional) | 2026-11-03 | synthetic |
| `synthetic_st-huberts-close_schedule-of-finishes_chiltern-vale_2026-09.pdf` | schedule_of_finishes | 3 | Chiltern Vale Developments Ltd (fictional) | 2026-09-15 | synthetic |

## Contradictions

| id | unit | field | type | sources (page) | values | expected resolution | voice agent says |
|---|---|---|---|---|---|---|---|
| C09 | no-59 | price | version_supersession | struttparker-a45c02cc p2; syn-shc59-price p1 | £1,458,000 guide; £1,395,000 from 9 Nov 2026 | Later formal instruction (tier 4, 3 Nov 2026) supersedes the April 2026 brochure (tier 5). Candidate £1,395,000; price is material so a human confirms. | Pending: don't quote. After sign-off: 'The guide price is £1,395,000.' |
| C10 | no-59 vs development | en_suite_fittings | scope_difference | syn-shc-finishes p1; struttparker-a45c02cc p2 | all en-suites walk-in showers (development scope); principal en suite BATHROOM; guest en suite shower room (unit scope) | Never copy the development-wide claim onto No. 59. Keep both at stated scope; the brochure is the only unit-level source. | For No. 59 say the particulars describe an en-suite bathroom to the principal bedroom and a shower room to the guest suite; don't say 'all en-suites have showers'. |
| C11 | no-59 (type E) vs plots 53/57 (type D) | en_suite_fittings / bedrooms | plot_or_type_variation | syn-shc-finishes p2; syn-shc-finishes p2 | No. 59 = type E, 5 bed, standard spec; type D = 4 bed, principal en-suite with freestanding bath | Resolve the entity first: No. 59 is type E. Never merge type D facts (4 bed, en-suite bath) into No. 59. | Answer only for No. 59; if the caller names another plot, treat it as a different property. |
