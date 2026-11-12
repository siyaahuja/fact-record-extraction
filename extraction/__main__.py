"""CLI.

  python -m extraction run  [sample_data] [--out out] [--extractor auto|rules|llm|hybrid]
  python -m extraction eval [--out out] [--golden eval/golden.json] [--manifest sample_data/manifest.json]
  python -m extraction all  (run, then eval)
  python -m extraction determinism [sample_data] [--runs 3]
"""
from __future__ import annotations

import argparse
import sys

from . import evaluate, pipeline


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m extraction")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "all"):
        p = sub.add_parser(name)
        p.add_argument("input", nargs="?", default="sample_data")
        p.add_argument("--out", default="out")
        p.add_argument("--extractor", default="auto", choices=["auto", "rules", "llm", "hybrid"])
        p.add_argument("--cache", default=".cache")
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--llm-pages", default="scanned", choices=["scanned", "all"],
                       help="hybrid mode: send only scanned/garbled pages to the LLM, or every page")
    for name in ("eval", "all"):
        p = sub.choices.get(name) or sub.add_parser(name)
        if name == "eval":
            p.add_argument("--out", default="out")
            p.add_argument("input", nargs="?", default="sample_data")
            p.add_argument("--cache", default=".cache")
        p.add_argument("--golden", default="eval/golden.json")
        p.add_argument("--manifest", default=None)
        p.add_argument("--contradictions", default=None)
    p = sub.add_parser("determinism")
    p.add_argument("input", nargs="?", default="sample_data")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--extractor", default="auto", choices=["auto", "rules", "llm", "hybrid"])
    a = ap.parse_args(argv)
    if a.cmd == "determinism":
        from . import determinism
        return determinism.main(a.input, a.runs, extractor=a.extractor)
    if a.cmd in ("run", "all"):
        pipeline.run(a.input, a.out, extractor=a.extractor, cache_dir=a.cache, workers=a.workers, llm_pages=a.llm_pages)
    if a.cmd in ("eval", "all"):
        return evaluate.main(a.out, a.input, a.golden, a.manifest, a.contradictions, a.cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
