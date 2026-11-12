# Results (rules extractor, no LLM key)

`make eval` on the 6 documents in `sample_data/`:

| section | result |
|---|---|
| documents vs manifest (type, tier, issuer, pages, text layer, date, unit) | 48/48 |
| golden facts (`eval/golden.json`, incl. must-not-extract checks) | 56/56 |
| entities (which unit each document describes) | 6/6 |
| evidence facts from `contradictions.json` (value on the cited doc + page) | 25/25 |
| quote checks (78 quotes re-found; 286 tampered quotes rejected) | 364/364 |
| contradictions C01–C11 detected with the expected type | 11/11 |
| **overall** | **510/510 (100%)** |

Per document:

| doc | checks |
|---|---|
| carterjonas-98889981 (Kelso, April, scanned) | 23/23 |
| carterjonas-f8692efa (Kelso, October, scanned) | 20/20 |
| syn-kv-survey (measured survey) | 20/20 |
| struttparker-a45c02cc (No. 59, garbled text layer) | 13/13 |
| syn-shc-finishes (schedule of finishes) | 11/11 |
| syn-shc59-price (price change instruction) | 6/6 |

Hard cases (every check behind each must pass):

| case | checks |
|---|---|
| Kelso April 185 sq m / 2,700 sq ft flagged doc_error | 1/1 |
| net vs gross never conflated | 11/11 |
| 468 sq ft lower ground: basis unspecified | 3/3 |
| parking 1 per floor vs 6 total (scope) | 8/8 |
| No. 59 Caesar-shifted text decoded and quoted verbatim | 2/2 |
| type D plot facts never attached to No. 59 | 3/3 |
| quote validation rejects anything not verbatim | 1/1 |

Determinism (`make determinism`: 3 runs, each with an empty OCR/render cache):

| run | seconds | facts | eval | facts.jsonl | contradictions.jsonl |
|---|---|---|---|---|---|
| 1 | 13.1 | 78 | 510/510 | 1b451871dfa1 | 40799e7e1bae |
| 2 | 12.5 | 78 | 510/510 | 1b451871dfa1 | 40799e7e1bae |
| 3 | 12.7 | 78 | 510/510 | 1b451871dfa1 | 40799e7e1bae |

Run-to-run variance: none; all four output files are byte-identical.

Not yet verified: the LLM (hybrid) path against a real API, because no key was available. Its merge logic is
covered offline by `tests/test_llm_merge.py` with a stub provider.
