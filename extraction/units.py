"""Number, money and area parsing plus sq m / sq ft normalisation."""
from __future__ import annotations

import re

from .catalogue import SQ_M_TO_SQ_FT, UNIT_MISMATCH_TOLERANCE

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "single": 1, "double": 2, "triple": 3,
}

NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
SQFT = r"(?:sq\.?\s?f(?:ee)?t\.?|sqft|ft2|ft²|square\s+f(?:ee|oo)t)"
SQM = r"(?:sq\.?\s?m(?:etres|eters)?\.?|sqm|m2|m²|square\s+met(?:re|er)s)"
AREA_UNIT = rf"(?:{SQFT}|{SQM})"


def parse_number(text: str) -> float | None:
    text = text.strip().lower()
    if text in WORD_NUMBERS:
        return float(WORD_NUMBERS[text])
    m = re.search(NUM, text)
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


def parse_money(text: str) -> float | None:
    m = re.search(rf"£\s?({NUM})\s?(m(?:illion)?|k)?\b", text, re.I)
    if not m:
        return None
    amount = float(m.group(1).replace(",", ""))
    suffix = (m.group(2) or "").lower()
    if suffix.startswith("m"):
        amount *= 1_000_000
    elif suffix == "k":
        amount *= 1_000
    return amount


def area_unit(token: str) -> str | None:
    t = token.strip().lower()
    if re.fullmatch(SQFT, t, re.I):
        return "sq_ft"
    if re.fullmatch(SQM, t, re.I):
        return "sq_m"
    return None


def normalise_area(amount: float, unit: str) -> dict:
    if unit == "sq_ft":
        return {"sq_ft": round(amount, 1), "sq_m": round(amount / SQ_M_TO_SQ_FT, 1)}
    return {"sq_ft": round(amount * SQ_M_TO_SQ_FT, 1), "sq_m": round(amount, 1)}


def unit_pair_mismatch(sq_ft: float, sq_m: float) -> float:
    """Relative disagreement between a printed sq ft figure and a printed sq m figure."""
    converted = sq_m * SQ_M_TO_SQ_FT
    return abs(converted - sq_ft) / max(sq_ft, converted)


def is_doc_error(sq_ft: float, sq_m: float) -> bool:
    return unit_pair_mismatch(sq_ft, sq_m) > UNIT_MISMATCH_TOLERANCE


def fmt_num(x: float) -> str:
    return f"{int(x):,}" if float(x).is_integer() else f"{x:,}"
