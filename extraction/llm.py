"""Vision LLM extraction, one call per page, with strict structured output and a pluggable provider.

Provider selection (first match wins):
  FACTS_LLM_PROVIDER=anthropic|openai|xai  (explicit), else whichever key is set:
  ANTHROPIC_API_KEY -> anthropic, OPENAI_API_KEY -> openai, XAI_API_KEY -> xai.
Model override: FACTS_LLM_MODEL.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

from .catalogue import FIELDS
from .pdfio import Page

PROMPT_VERSION = "p3"
DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-5", "openai": "gpt-4.1", "xai": "grok-4"}


def _nullable(t: str, enum: list | None = None, desc: str | None = None) -> dict:
    s: dict = {"type": [t, "null"]}
    if enum:
        s["enum"] = enum + [None]
    if desc:
        s["description"] = desc
    return s


def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


QUALIFIER = _obj({
    "type": _nullable("string", ["guide", "asking", "offers_over", "offers_in_region", "poa", "contracted", "current", "potential"],
                      "price: guide|asking|offers_over|offers_in_region|poa|contracted. epc_rating: current|potential"),
    "period": _nullable("string", ["annum", "month", "week"], "rent/ground_rent/service_charge period"),
    "per": _nullable("string", ["unit", "floor"], "rent: per floor only if printed as each/per floor"),
    "basis": _nullable("string", ["NIA", "GIA", "IPMS", "EPC", "unspecified"],
                       "floor_area basis exactly as printed; 'unspecified' if no basis is printed"),
    "scope": _nullable("string", None, "floor_area/availability: whole | floor:<lower_ground|ground|first|...> | part:<name> | "
                                        "house_type:<id> | plot:<id>. parking: total|per_unit|per_floor"),
    "kind": _nullable("string", None, "incentive kind"),
    "room": _nullable("string", None, "room for bathroom_fixture/room_dimension, e.g. principal_en_suite"),
    "item": _nullable("string", None, "finish item"),
    "measure": _nullable("string", ["years_remaining", "term_from"]),
})
VALUE = _obj({
    "amount": _nullable("number", None, "money in GBP or area amount in the unit stated FIRST in value_raw"),
    "currency": _nullable("string", ["GBP"]),
    "unit": _nullable("string", ["sq_ft", "sq_m", "acre", "hectare"]),
    "tenure": _nullable("string", ["freehold", "leasehold", "share_of_freehold", "commonhold"]),
    "type": _nullable("string", ["for_sale", "to_let", "for_sale_or_to_let"], "transaction_type value"),
    "band": _nullable("string", ["A+", "A", "B", "C", "D", "E", "F", "G"]),
    "score": _nullable("integer"),
    "certificate_date": _nullable("string", None, "ISO date if printed"),
    "spaces": _nullable("integer"),
    "kind": _nullable("string", ["allocated", "garage", "on_street", "permit", "unspecified"], "parking kind"),
    "count": _nullable("integer", None, "bedrooms/bathrooms"),
    "status": _nullable("string", ["available", "reserved", "under_offer", "sold", "let"]),
    "fixture": _nullable("string", ["bath", "shower", "both"]),
    "grade": _nullable("string", None, "listed_status grade"),
    "text": _nullable("string"),
})
FACT = _obj({
    "field": {"type": "string", "enum": sorted(FIELDS)},
    "value_raw": {"type": "string", "description": "the value exactly as printed, e.g. '£600,000' or '185 | 2,700'"},
    "quote": {"type": "string", "description": "verbatim span copied from the page (one line or sentence) that contains value_raw"},
    "qualifier": QUALIFIER,
    "value": VALUE,
    "paired_value": {"anyOf": [_obj({"amount": {"type": "number"}, "unit": {"type": "string", "enum": ["sq_ft", "sq_m"]}}), {"type": "null"}],
                     "description": "floor_area only: the same area printed in the other unit on the same line/row"},
    "unit_hint": _nullable("string", None, "what the fact is about as printed, e.g. 'whole building', 'lower ground floor', 'No. 59'"),
    "confidence": {"type": "number"},
})
SCHEMA = _obj({"facts": {"type": "array", "items": FACT}})

SYSTEM = """You extract property facts from ONE page of a property document for a verified fact record.
Rules:
- Only report facts printed on this page. Never infer, never compute, never use outside knowledge.
- quote: copy a verbatim span (a line, table row or sentence) from the page that contains the value. Copy characters exactly as printed (keep £, commas, units). If the text layer below is garbled, quote what you read in the image.
- value_raw: the value as printed (for a table row give both cells, e.g. '185 | 2,700').
- Core fields (be exhaustive): price, rent, tenure, transaction_type, floor_area, epc_rating, parking. Also report bedrooms, bathrooms, bathroom_fixture, availability, listed_status, covenant, lease_length when printed.
- price: skip historical prices (previous prices, price paid, reductions); report the current one. 'offers will be considered at £X' = offers_in_region; 'offers in excess of' = offers_over.
- floor_area: one fact per printed area. basis only if the words NIA/net/GIA/gross/IPMS (or an EPC 'total floor area') are printed for that figure or its table column/heading; otherwise 'unspecified'. Never default to net. scope: 'whole' for whole building/house totals, 'floor:<name>' for a named floor (lower_ground, ground, first, second ...), 'part:<name>' for a garage or other part, 'house_type:<id>' or 'plot:<id>' for rows of a type/plot table. Put the first printed unit in value and the other printed unit of the SAME figure in paired_value, even if the two disagree (do not correct document errors).
- parking scope: per_floor if printed per/each floor, per_unit if per unit/flat, else total. Report each statement separately.
- epc_rating: one fact per printed rating, with qualifier.type current or potential.
- Areas or prices that the page attributes to ANOTHER document (e.g. 'quoted in the marketing particulars') are not facts of this page: skip them.
- Use null for every qualifier/value key that does not apply to the field.
"""


class Provider:
    name = "base"

    def __init__(self, model: str, cache_dir: str):
        self.model = model
        self.cache_dir = os.path.join(cache_dir, "llm")
        os.makedirs(self.cache_dir, exist_ok=True)

    def extract(self, system: str, text: str, image_png: bytes) -> dict:
        key = hashlib.sha256(f"{self.name}|{self.model}|{PROMPT_VERSION}|{system}|{text}".encode() + image_png).hexdigest()
        path = os.path.join(self.cache_dir, f"{key[:24]}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        out = self._call(system, text, image_png)
        with open(path, "w") as f:
            json.dump(out, f)
        return out

    def _call(self, system: str, text: str, image_png: bytes) -> dict:
        raise NotImplementedError


class AnthropicProvider(Provider):
    name = "anthropic"

    def _call(self, system, text, image_png):
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model, max_tokens=8000, system=system, temperature=0,
            tools=[{"name": "record_facts", "description": "Record the facts found on the page.", "input_schema": SCHEMA}],
            tool_choice={"type": "tool", "name": "record_facts"},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(image_png).decode()}},
                {"type": "text", "text": text},
            ]}],
        )
        for block in msg.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("model returned no tool call")


class OpenAICompatibleProvider(Provider):
    name = "openai"
    base_url = None
    key_env = "OPENAI_API_KEY"

    def _call(self, system, text, image_png):
        from openai import OpenAI
        client = OpenAI(api_key=os.environ[self.key_env], base_url=self.base_url)
        resp = client.chat.completions.create(
            model=self.model, temperature=0,
            response_format={"type": "json_schema", "json_schema": {"name": "page_facts", "strict": True, "schema": SCHEMA}},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image_png).decode()}},
                {"type": "text", "text": text},
            ]}],
        )
        return json.loads(resp.choices[0].message.content)


class XAIProvider(OpenAICompatibleProvider):
    name = "xai"
    base_url = "https://api.x.ai/v1"
    key_env = "XAI_API_KEY"


PROVIDERS = {"anthropic": (AnthropicProvider, "ANTHROPIC_API_KEY"), "openai": (OpenAICompatibleProvider, "OPENAI_API_KEY"),
             "xai": (XAIProvider, "XAI_API_KEY")}


def get_provider(cache_dir: str = ".cache") -> Provider | None:
    explicit = os.environ.get("FACTS_LLM_PROVIDER")
    order = [explicit] if explicit else ["anthropic", "openai", "xai"]
    for name in order:
        cls, env = PROVIDERS[name]
        if os.environ.get(env):
            return cls(os.environ.get("FACTS_LLM_MODEL", DEFAULT_MODELS[name]), cache_dir)
    return None


def page_prompt(page: Page, meta: dict) -> str:
    status = page.text_status
    note = {"none": "No text layer: read the image (OCR text below may be incomplete).",
            "sparse": "Text layer nearly empty: read the image (OCR text below).",
            "garbled": "Text layer is GARBLED (broken font encoding): read the image; the repaired/OCR text below is a hint only.",
            "partial_garbled": "Parts of the text layer were garbled and have been repaired; trust the image if they disagree.",
            "good": "Text layer is good."}[status]
    return (f"Document: {meta['doc_id']} | guessed type: {meta['doc_type']} | issuer: {meta.get('issuer_org')}\n"
            f"Page {page.page_no} of the document. {note}\n\n--- page text ---\n{page.best_text()[:7000]}")


def to_candidate(f: dict, page_no: int) -> dict:
    field = f.get("field")
    allowed = FIELDS.get(field, {})
    qual = {k: v for k, v in (f.get("qualifier") or {}).items() if v is not None and k in allowed}
    if field == "floor_area":
        qual.setdefault("basis", "unspecified")
    value = {k: v for k, v in (f.get("value") or {}).items() if v is not None}
    if field in ("price", "rent", "ground_rent", "service_charge"):
        value.setdefault("currency", "GBP")
    if field == "parking":
        value.setdefault("kind", "unspecified")
    return {
        "field": field, "qualifier": qual, "value": value, "value_raw": f.get("value_raw") or "",
        "quote": f.get("quote") or "", "page": page_no, "paired": f.get("paired_value"),
        "confidence": f.get("confidence", 0.8), "extraction_method": "llm_vision", "text_source": "llm",
        "unit_hint": f.get("unit_hint"),
    }


def llm_extract_page(provider: Provider, page: Page, meta: dict) -> list[dict]:
    with open(page.image_path, "rb") as fh:
        image = fh.read()
    out = provider.extract(SYSTEM, page_prompt(page, meta), image)
    return [to_candidate(f, page.page_no) for f in out.get("facts", [])]
