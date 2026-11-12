# fact-record-extraction

Turns a folder of property PDFs (agent brochures, surveys, solicitor letters, schedules) into **verified fact
records**: one JSONL line per fact, each with the document, page, verbatim quote, date and issuer it came from,
following `docs/fact-record-schema.md`. It also flags contradictions between documents using the spec's seven types.

## Run it locally

```bash
git clone https://github.com/siyaahuja/fact-record-extraction.git
cd fact-record-extraction
git checkout cursor/extraction-pipeline-981f      # until the PR is merged

# system dependency: Tesseract OCR (Kelso brochures are scans)
sudo apt-get install -y tesseract-ocr              # macOS: brew install tesseract
python3 -m pip install -r requirements.txt         # Python 3.10+

make eval          # extract sample_data/ -> out/, then score it (exit 0 = everything passes)
```

Or without make:

```bash
python3 -m extraction run sample_data --out out    # extraction
python3 -m extraction eval sample_data --out out   # evaluation tables + overall score
python3 -m extraction determinism --runs 3         # 3 cold runs, byte-for-byte comparison
python3 -m unittest discover -s tests -t .         # offline test of the LLM merge (stub provider)
```

Outputs land in `out/`:

| file | contents |
|---|---|
| `facts.jsonl` | accepted facts: field, qualifier, value, normalised sq ft/sq m, page, quote, doc_error, unit, tier, as_at |
| `contradictions.jsonl` | contradiction groups: type, fact_ids, values, recommended candidate, rule applied |
| `documents.jsonl` | per-document classification: doc_type, tier, issuer, date (+source), text layer per page, unit |
| `rejected.jsonl` | candidates that failed validation (quote not on page, value not printed, unknown field...) and why |
| `summary.md` / `summary.json` | human-readable per-document summary |
| `eval.json` | scores from the last `eval` |

## LLM (optional)

The deterministic rules extractor is the primary path and needs no key. With a key, `--extractor auto` (default)
becomes `hybrid`: a vision LLM reads the pages whose text layer can't be trusted (scanned / garbled), at
temperature 0 with a strict JSON schema, and its answers are cached on disk (`.cache/llm/`), so reruns replay
identically. Rules facts always win; the LLM marks them `cross_check: llm_agrees`, disagreements go to
`rejected.jsonl` for review, and LLM facts are only added for a page+field the rules found nothing for. Every LLM
fact passes the same quote validator.

| env var | provider (default model) |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic (`claude-sonnet-4-5`) — preferred |
| `OPENAI_API_KEY` | OpenAI (`gpt-4.1`) |
| `XAI_API_KEY` | xAI (`grok-4`) |

`FACTS_LLM_PROVIDER=anthropic|openai|xai` picks one when several keys are set; `FACTS_LLM_MODEL` overrides the
model; `--extractor rules` forces the rules-only path; `--llm-pages all` sends every page to the LLM.

## How it works

`extraction/pdfio.py` renders each page (PyMuPDF), keeps the text layer, OCRs the page in colour with
Tesseract (plus white-on-dark banners, column by column) and detects/repairs Caesar-shifted text layers (No. 59).
`classify.py` assigns doc type, issuer, date and the development/unit. `rules.py` extracts price, rent, tenure,
transaction type, floor areas (basis and scope kept separate; never inferred), EPC, parking (with scope),
bedrooms/bathrooms and fittings, including tables read from word coordinates. `validate.py` rejects any fact whose
quote is not verbatim on its page (OCR slips of 1-2 non-digit characters tolerated, nothing else) and recomputes
unit conversions and `doc_error` (sq m vs sq ft disagreeing by more than 2%). `contradictions.py` groups facts per
unit and classifies conflicts. `evaluate.py` scores everything against `sample_data/manifest.json`,
`sample_data/contradictions.json` and `eval/golden.json`. Latest results: `RESULTS.md`.
