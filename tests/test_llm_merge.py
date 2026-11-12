"""Offline check of the hybrid path: a stub provider stands in for the LLM so the merge is tested without a key."""
import json
import os
import tempfile
import unittest

from extraction import pipeline
from extraction.llm import Provider

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample_data")
APRIL = "carterjonas-98889981"


class StubProvider(Provider):
    name = "stub"

    def __init__(self, cache_dir):
        super().__init__("stub-model", cache_dir)
        self.calls = 0

    def extract(self, system, text, image_png):
        self.calls += 1
        if f"Document: {APRIL}" not in text or "Page 2 " not in text:
            return {"facts": []}
        return {"facts": [
            # agrees with the rules fact
            {"field": "epc_rating", "value_raw": "B", "quote": "EPC has been assessed as B.",
             "qualifier": {"type": "current"}, "value": {"band": "B"}},
            # same slot, different value: rules fact kept, LLM fact rejected for review
            {"field": "price", "value_raw": "£700,000", "quote": "£700,000",
             "qualifier": {"type": "guide"}, "value": {"amount": 700000}},
            # quote not on the page: rejected by the validator
            {"field": "tenure", "value_raw": "leasehold", "quote": "The property is offered leasehold with 999 years",
             "qualifier": {}, "value": {"tenure": "leasehold"}},
        ]}


class HybridMergeTest(unittest.TestCase):
    def test_rules_primary_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = []
            for i in range(2):
                provider = StubProvider(os.path.join(tmp, "llmcache"))
                out = os.path.join(tmp, f"out{i}")
                pipeline.run(SAMPLE, out, extractor="hybrid", provider=provider, log=lambda *a: None)
                self.assertGreater(provider.calls, 0)
                with open(os.path.join(out, "facts.jsonl")) as f:
                    outs.append(f.read())
            self.assertEqual(outs[0], outs[1])
            facts = [json.loads(l) for l in outs[0].splitlines()]
            with open(os.path.join(tmp, "out0", "rejected.jsonl")) as f:
                rejected = [json.loads(l) for l in f]

        epc = [f for f in facts if f["doc_id"] == APRIL and f["field"] == "epc_rating"]
        self.assertTrue(epc and all(f["extraction_method"] == "regex" for f in epc))
        self.assertIn("llm_agrees", {f.get("cross_check") for f in epc})
        self.assertFalse([f for f in facts if f["field"] == "tenure" and f["value"].get("tenure") == "leasehold"])
        self.assertTrue([r for r in rejected if r["field"] == "tenure" and r["reason"] == "quote_not_found"])
        prices = [f for f in facts if f["doc_id"] == APRIL and f["field"] == "price"]
        self.assertTrue(prices and all(f["extraction_method"] == "regex" for f in prices))


if __name__ == "__main__":
    unittest.main()
