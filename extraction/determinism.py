"""Run the whole pipeline N times from a cold cache and compare the outputs byte for byte."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import time

from . import evaluate, pipeline

OUTPUTS = ("documents.jsonl", "facts.jsonl", "contradictions.jsonl", "rejected.jsonl")


def _digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def main(input_dir="sample_data", runs=3, work=".determinism", extractor="auto") -> int:
    shutil.rmtree(work, ignore_errors=True)
    rows = []
    for i in range(1, runs + 1):
        cache, out = os.path.join(work, f"cache{i}"), os.path.join(work, f"out{i}")
        t = time.time()
        pipeline.run(input_dir, out, extractor=extractor, cache_dir=cache, log=lambda *a: None)
        secs = time.time() - t
        with contextlib.redirect_stdout(io.StringIO()):
            evaluate.main(out, input_dir, cache_dir=cache)
        with open(os.path.join(out, "eval.json")) as f:
            overall = json.load(f)["overall"]
        with open(os.path.join(out, "facts.jsonl")) as f:
            n_facts = sum(1 for _ in f)
        rows.append({"run": i, "seconds": round(secs, 1), "facts": n_facts,
                     "eval": f"{overall['passed']}/{overall['total']}",
                     **{name: _digest(os.path.join(out, name)) for name in OUTPUTS}})
    print(f"\nDETERMINISM: {runs} cold runs (fresh OCR/render/LLM cache each run)")
    header = ["run", "seconds", "facts", "eval"] + list(OUTPUTS)
    print("  ".join(f"{h:<20}" if h in OUTPUTS else f"{h:<8}" for h in header))
    for r in rows:
        print("  ".join(f"{r[h]!s:<20}" if h in OUTPUTS else f"{r[h]!s:<8}" for h in header))
    identical = all(all(r[n] == rows[0][n] for n in OUTPUTS) for r in rows)
    print(f"run-to-run variance: {'none (all outputs byte-identical)' if identical else 'OUTPUTS DIFFER'}")
    return 0 if identical else 1
