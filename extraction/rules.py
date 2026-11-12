"""Deterministic extractor over page text (pdf text layer, repaired text, OCR).

It runs without any model and gives the eval a floor; the LLM extractor adds recall and
better scope reading. Every candidate still goes through validate.py.
"""
from __future__ import annotations

import re

from .pdfio import Page, Row
from .units import AREA_UNIT, NUM, WORD_NUMBERS, area_unit, parse_money, parse_number

DATE_ISO_RE = r"\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}"
WORDNUM = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))
COUNT = rf"(?:\d{{1,3}}|{WORDNUM})"
FLOOR_RE = r"(lower\s+ground|upper\s+ground|ground|first|second|third|fourth|fifth|basement|lower|mezzanine|attic)\s+floor"
FLOOR_SYNONYMS = {"lower": "lower_ground"}
BASIS_RE = [
    (r"\bNIA\b|net\s+internal|\bnet\b", "NIA"),
    (r"\bGIA\b|gross\s+internal|\bgross\b", "GIA"),
    (r"\bIPMS\b", "IPMS"),
]


def floor_slug(name: str) -> str:
    s = re.sub(r"\s+", "_", name.strip().lower())
    return FLOOR_SYNONYMS.get(s, s)


def squash(s: str) -> str:
    return re.sub(r"[^a-z0-9£]", "", s.lower())


def _line_span(text: str, start: int, end: int) -> str:
    """Quote = the full line(s) covering the match, whitespace collapsed, trimmed if long."""
    a = text.rfind("\n", 0, start) + 1
    b = text.find("\n", end)
    b = len(text) if b == -1 else b
    quote = text[a:b]
    if len(quote) > 260:
        rel_s, rel_e = start - a, end - a
        lo = max(0, rel_s - 100)
        hi = min(len(quote), rel_e + 100)
        while lo > 0 and not quote[lo - 1].isspace():
            lo -= 1
        while hi < len(quote) and not quote[hi].isspace():
            hi += 1
        quote = quote[lo:hi]
    return re.sub(r"\s+", " ", quote).strip()


def _clause_after(text: str, end: int, limit: int = 60) -> str:
    seg = text[end:end + limit]
    m = re.search(r"[.;]|\band\b|\n\s*\n", seg)
    return seg[: m.start()] if m else seg


def _clause_before(text: str, start: int, limit: int = 60) -> str:
    seg = text[max(0, start - limit):start]
    m = None
    for m in re.finditer(r"[.;]\s|\band\b|\n\s*\n", seg):
        pass
    return seg[m.end():] if m else seg


class Ctx:
    def __init__(self, page: Page, doc_type: str, focus_floor: str | None):
        self.page = page
        self.doc_type = doc_type
        self.focus_floor = focus_floor
        self.out: list[dict] = []

    def add(self, source: str, field: str, qualifier: dict, value: dict, value_raw: str, quote: str, **extra):
        self.out.append({
            "field": field, "qualifier": qualifier, "value": value, "value_raw": value_raw.strip(),
            "quote": quote, "page": self.page.page_no, "extraction_method": "regex",
            "text_source": source, "confidence": extra.pop("confidence", 0.8), **extra,
        })


# ---------------------------------------------------------------- price and rent

PRICE_TYPE_CUES = [
    (r"guide\s+price|\bguide\b", "guide"),
    (r"asking\s+price", "asking"),
    (r"offers\s+(?:over|in\s+excess\s+of|above)", "offers_over"),
    (r"offers\s+in\s+the\s+region\s+of|\boiro\b|offers\s+around", "offers_in_region"),
    (r"offers\s+will\s+be\s+considered(?:\s+[\w,]+){0,6}?\s+at|offers\s+at", "offers_in_region"),
    (r"contract\s+price|purchase\s+price", "contracted"),
]
PRICE_EXCLUDE = r"previous|\bwas\b|paid|reduced\s+from|\bfrom\b|change|fee|deposit|stamp\s+duty|referral|service\s+charge|ground\s+rent|council\s+tax"
RENT_PERIOD = [
    (r"per\s+annum|\bp\.?\s?a\.?(?![a-z])|per\s+year|a\s+year", "annum"),
    (r"per\s+calendar\s+month|\bpcm\b|per\s+month|a\s+month", "month"),
    (r"per\s+week|\bpw\b|a\s+week", "week"),
]


def _nearest(cues, text: str):
    best = None
    for rx, label in cues:
        for m in re.finditer(rx, text, re.I):
            if best is None or m.end() > best[0]:
                best = (m.end(), label)
    return best


def extract_money(ctx: Ctx, source: str, text: str):
    for m in re.finditer(rf"(?<![\w−-])£\s?({NUM})(\s?(?:m(?:illion)?|k)\b)?", text, re.I):
        amount = parse_money(m.group(0))
        if amount is None:
            continue
        post = text[m.end(): m.end() + 45]
        pre = text[max(0, m.start() - 90): m.start()]
        quote = _line_span(text, m.start(), m.end())
        if re.match(r"\s*per\s+sq|\s*psf", post, re.I):
            continue
        period = None
        for rx, label in RENT_PERIOD:
            if re.match(rf"[\s,]*(?:exclusive[\s,]*)?(?:{rx})", post, re.I):
                period = label
                break
        if period:
            if re.search(r"ground\s+rent|service\s+charge", pre[-40:], re.I):
                continue
            per = "floor" if re.search(r"each\s+floor|per\s+floor", post + pre[-30:], re.I) else "unit"
            fl = re.search(FLOOR_RE.replace(r"\s+floor", r"(?:\s+floor)?"), pre[-30:], re.I)
            qual = {"period": period, "per": per}
            ctx.add(source, "rent", qual, {"amount": amount, "currency": "GBP"}, m.group(0) + text[m.end():m.end() + 12].split("\n")[0],
                    quote, unit_floor=floor_slug(fl.group(1)) if fl else None)
            continue
        if amount < 10_000:
            continue
        post_type = _nearest(PRICE_TYPE_CUES, post[:22])
        pre_cue = _nearest(PRICE_TYPE_CUES + [(PRICE_EXCLUDE, "_exclude"), (r"revised|reduced\s+to|\bnow\b|new\s+price", "_revised")], pre)
        if pre_cue and pre_cue[1] == "_exclude" and not post_type:
            continue
        if re.search(r"[−-]\s*$", pre):
            continue
        if post_type:
            ptype = post_type[1]
        elif pre_cue and pre_cue[1] == "_revised":
            wider = text[max(0, m.start() - 300): m.start()]
            t = _nearest(PRICE_TYPE_CUES, wider)
            ptype = t[1] if t else "asking"
        elif pre_cue:
            ptype = pre_cue[1]
        elif re.search(r"\bprice\b", pre[-40:], re.I):
            ptype = "asking"
        else:
            continue
        ctx.add(source, "price", {"type": ptype}, {"amount": amount, "currency": "GBP"}, m.group(0), quote)


# ---------------------------------------------------------------- tenure, transaction type

def extract_tenure(ctx: Ctx, source: str, text: str):
    for m in re.finditer(r"\b(share\s+of\s+freehold|freehold|leasehold|commonhold)\b", text, re.I):
        val = re.sub(r"\s+", "_", m.group(1).lower())
        ctx.add(source, "tenure", {}, {"tenure": val}, m.group(1), _line_span(text, m.start(), m.end()))
    for m in re.finditer(r"\b(for\s+sale\s+or\s+to\s+let|for\s+sale|to\s+let)\b", text, re.I):
        raw = re.sub(r"\s+", " ", m.group(1).lower())
        val = {"for sale or to let": "for_sale_or_to_let", "for sale": "for_sale", "to let": "to_let"}[raw]
        if val == "to_let" and re.search(r"or\s*$", text[max(0, m.start() - 6):m.start()], re.I):
            continue
        ctx.add(source, "transaction_type", {}, {"type": val}, m.group(1), _line_span(text, m.start(), m.end()))


# ---------------------------------------------------------------- floor area

def _basis(text: str, start: int, end: int, prev_end: int, next_start: int, lines_before: list[str]) -> str:
    immediate = text[max(prev_end, start - 8):start]
    after = text[end:min(next_start, end + 30)]
    before = text[max(prev_end, start - 40):start]
    for window in (immediate, after, before):
        for rx, label in BASIS_RE:
            if re.search(rx, window, re.I):
                return label
    for line in lines_before:
        if re.search(r"\d", line):
            continue
        hits = {label for rx, label in BASIS_RE if re.search(rx, line, re.I)}
        if len(hits) == 1:
            return hits.pop()
    return "unspecified"


def _scope(ctx: Ctx, line_prefix: str, lines_before: list[str]) -> str:
    fl = re.search(FLOOR_RE, line_prefix, re.I)
    if fl:
        return f"floor:{floor_slug(fl.group(1))}"
    if re.search(r"garage", line_prefix, re.I):
        return "part:garage"
    if re.search(r"total|whole|all\s+floors|house|building|overall", line_prefix, re.I):
        return "whole"
    for line in lines_before[:2]:
        if re.search(r"\d", line):
            continue
        fl = re.search(FLOOR_RE, line, re.I)
        if fl:
            return f"floor:{floor_slug(fl.group(1))}"
    if ctx.focus_floor:
        return f"floor:{ctx.focus_floor}"
    return "whole"


AREA_PAIR = rf"({NUM})\s*({AREA_UNIT})\s*[\(/|]\s*({NUM})\s*({AREA_UNIT})\s*\)?"
AREA_ONE = rf"({NUM})\s*({AREA_UNIT})(?![a-z])"
AREA_EXCLUDE_AFTER = r"\s*\)?\s*(?:quoted\s+in|stated\s+in|in\s+(?:current\s+)?marketing|per\s+the\s+(?:brochure|particulars))"


def extract_area(ctx: Ctx, source: str, text: str):
    spans = []
    for m in re.finditer(AREA_PAIR, text, re.I):
        u1, u2 = area_unit(m.group(2)), area_unit(m.group(4))
        if u1 and u2 and u1 != u2:
            spans.append((m.start(), m.end(), [(parse_number(m.group(1)), u1), (parse_number(m.group(3)), u2)], m.group(0)))
    taken = [(s, e) for s, e, *_ in spans]
    for m in re.finditer(AREA_ONE, text, re.I):
        if any(s <= m.start() < e for s, e in taken):
            continue
        u = area_unit(m.group(2))
        if u:
            spans.append((m.start(), m.end(), [(parse_number(m.group(1)), u)], m.group(0)))
    spans.sort()
    for i, (start, end, vals, raw) in enumerate(spans):
        if re.match(AREA_EXCLUDE_AFTER, text[end:end + 60], re.I) or re.match(r"\s*=", text[end:end + 5]):
            continue
        if re.search(r"(?:than|from|vs\.?|versus)\s+(?:the\s+)?$", text[max(0, start - 15):start], re.I):
            continue
        if re.search(r"/\s*$|per\s+$|=\s*$", text[max(0, start - 5):start]):
            continue
        prev_end = spans[i - 1][1] if i else 0
        next_start = spans[i + 1][0] if i + 1 < len(spans) else len(text)
        line_start = text.rfind("\n", 0, start) + 1
        before_lines = [l.strip() for l in text[:line_start].splitlines()[-4:]][::-1]
        basis = _basis(text, start, end, prev_end, next_start, before_lines)
        lead = text[max(0, start - 60):start]
        if basis == "unspecified" and ((ctx.doc_type == "epc_certificate" and re.search(r"floor\s+area", lead, re.I))
                                       or re.search(r"useful\s+floor\s+area", lead, re.I)):
            basis = "EPC"
        scope = _scope(ctx, text[line_start:start], before_lines)
        (amount, unit) = vals[0]
        pair = vals[1] if len(vals) > 1 else None
        ctx.add(source, "floor_area", {"basis": basis, "scope": scope}, {"amount": amount, "unit": unit}, raw,
                _line_span(text, start, end), paired=({"amount": pair[0], "unit": pair[1]} if pair else None))


def _header_columns(row: Row):
    """Find area-unit columns in a table header row: [(x0, x1, unit, basis)]."""
    words = row.words
    cols = []
    i = 0
    while i < len(words):
        two = " ".join(w.text for w in words[i:i + 2])
        one = words[i].text
        unit, width = None, 1
        if area_unit(two.rstrip(".,:")) and i + 1 < len(words):
            unit, width = area_unit(two.rstrip(".,:")), 2
        elif area_unit(one.rstrip(".,:")):
            unit = area_unit(one.rstrip(".,:"))
        if unit:
            if i > 0 and re.fullmatch(NUM, words[i - 1].text.replace("(", "")):
                return []
            basis = None
            j = i - 1
            prev_x = cols[-1][1] if cols else -1
            while j >= 0 and words[j].x0 > prev_x:
                token = words[j].text.strip("()")
                for rx, label in BASIS_RE:
                    if re.fullmatch(rx, token, re.I):
                        basis = label
                if words[j].x1 < (words[i].x0 - 80):
                    break
                j -= 1
            if basis is None and cols:
                basis = cols[-1][3]
            cols.append((words[i].x0, words[i + width - 1].x1, unit, basis))
            i += width
        else:
            i += 1
    return cols


def extract_area_tables(ctx: Ctx):
    rows = ctx.page.rows
    for hi, header in enumerate(rows):
        cols = _header_columns(header)
        if not cols:
            continue
        first_col_x0 = cols[0][0]
        if header.source == "pdf_text":
            table_left = header.words[0].x0
        else:
            left = [w for w in header.words if w.x1 < first_col_x0 and not re.fullmatch(r"\(?(NIA|GIA|IPMS)\)?", w.text)]
            table_left = left[-1].x0 if left else first_col_x0
        table_right = cols[-1][1] + 25
        spacing = min([b[0] - a[0] for a, b in zip(cols, cols[1:])] or [80])
        tol = max(12.0, 0.55 * spacing)
        type_table = re.match(r"(house\s+)?type|plot", header.words[0].text, re.I) and header.source == "pdf_text"
        data_rows = []
        for row in rows[hi + 1: hi + 14]:
            if row.source != header.source:
                continue
            if _header_columns(row) or (row.source == "pdf_text" and re.search(r"[a-z]{3,}\.\s", row.text)):
                break
            cells = {}
            for ci, (x0, x1, unit, basis) in enumerate(cols):
                cx = (x0 + x1) / 2
                best = None
                for w in row.words:
                    if re.fullmatch(NUM, w.text) and abs(w.xc - cx) < tol and (best is None or abs(w.xc - cx) < abs(best.xc - cx)):
                        best = w
                if best:
                    cells[ci] = best
            if len(cells) < max(1, (len(cols) + 1) // 2):
                # OCR rows interleave prose from neighbouring page columns, so only stop on PDF text.
                if data_rows and row.source == "pdf_text":
                    break
                continue
            label_words = [w for w in row.words if w.x0 >= table_left - 5 and w.x1 <= first_col_x0 - 2
                           and not (type_table and re.fullmatch(NUM, w.text))]
            label = " ".join(w.text for w in label_words)
            in_table = [w for w in row.words if w.x0 >= table_left - 5 and w.x0 <= table_right]
            quote = " ".join(w.text for w in in_table)
            data_rows.append((label, cells, quote))
        for k, (label, cells, quote) in enumerate(data_rows):
            values = {ci: parse_number(w.text) for ci, w in cells.items()}
            if (re.fullmatch(r"total", label.strip(), re.I) and k == 1
                    and {ci: parse_number(w.text) for ci, w in data_rows[0][1].items()} == values):
                continue
            if type_table:
                scope = f"house_type:{label.split()[0].upper()}" if label else "whole"
            else:
                fl = re.search(FLOOR_RE, label, re.I)
                scope = (f"floor:{floor_slug(fl.group(1))}" if fl else
                         "whole" if re.search(r"total|all\s+floors|whole|building", label, re.I) or not label else
                         f"part:{re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')}")
            used = set()
            for ci in sorted(values):
                if ci in used:
                    continue
                x0, x1, unit, basis = cols[ci]
                pair = None
                for cj in sorted(values):
                    if cj != ci and cj not in used and cols[cj][2] != unit and cols[cj][3] == basis:
                        pair = cj
                        break
                used.add(ci)
                if pair is not None:
                    used.add(pair)
                raw = cells[ci].text + (f" | {cells[pair].text}" if pair is not None else "")
                ctx.add(header.source + "_table", "floor_area", {"basis": basis or "unspecified", "scope": scope},
                        {"amount": values[ci], "unit": unit}, raw, quote,
                        paired=({"amount": values[pair], "unit": cols[pair][2]} if pair is not None else None),
                        table_header=header.text, unit_hint=label or None)


# ---------------------------------------------------------------- EPC

def extract_epc(ctx: Ctx, source: str, text: str):
    for m in re.finditer(r"\bEPC\)?\s*(?:rating|band)?\s*(?:has\s+been\s+assessed\s+as|is|of|:|-)?\s*\b([A-G])\b(?![\w'’])", text):
        ctx.add(source, "epc_rating", {"type": "current"}, {"band": m.group(1)}, m.group(0), _line_span(text, m.start(), m.end()))
    for m in re.finditer(r"current\s+energy\s+(?:efficiency\s+)?rating\s+is\s+([A-G])\b|energy\s+rating\s*(?:is|:)\s*([A-G])\b", text, re.I):
        band = m.group(1) or m.group(2)
        val = {"band": band}
        score = re.search(rf"^\s*(\d{{1,3}})\s+{band}\s*$", text, re.M)
        if score:
            val["score"] = int(score.group(1))
        d = re.search(r"date\s+of\s+certificate\s*\n?\s*(\d{1,2}\s+\w+\s+\d{4})", text, re.I)
        if d:
            val["certificate_date"] = d.group(1)
        ctx.add(source, "epc_rating", {"type": "current"}, val, m.group(0), _line_span(text, m.start(), m.end()))
    for m in re.finditer(r"\b(?:asset\s+rating\s+of\s+(\d{1,3}),?\s+)?band\s+([A-G])\b", text, re.I):
        context = text[max(0, m.start() - 250):m.start()]
        if not re.search(r"\bEPC\b|energy\s+performance", context, re.I):
            continue
        val = {"band": m.group(2)}
        if m.group(1):
            val["score"] = int(m.group(1))
        extra = {}
        cert = re.search(r"certificate\s*\n?\s*(\d{4}(?:-\d{4}){4})", context)
        if cert:
            dated = re.search(DATE_ISO_RE, text[cert.end():cert.end() + 60], re.I)
            extra["cites_official_record"] = {"type": "epc_certificate", "ref": cert.group(1),
                                              "date": dated.group(0) if dated else None}
        ctx.add(source, "epc_rating", {"type": "current"}, val, m.group(0), _line_span(text, m.start(), m.end()), **extra)
    for m in re.finditer(r"potential\s+to\s+be\s+([A-G])\b", text, re.I):
        ctx.add(source, "epc_rating", {"type": "potential"}, {"band": m.group(1)}, m.group(0), _line_span(text, m.start(), m.end()))


# ---------------------------------------------------------------- parking

def extract_parking(ctx: Ctx, source: str, text: str):
    pat = rf"\b({COUNT})(?:\s*\((\d+)\))?\s+(?:allocated\s+|marked\s+|car\s+)?(?:parking\s+)?(spaces?|bays?)\b"
    for m in re.finditer(pat, text, re.I):
        n = parse_number(m.group(2) or m.group(1))
        if not n or n > 500:
            continue
        before = text[max(0, m.start() - 25):m.start()]
        if not re.search(r"park|car", before + m.group(0) + text[m.end():m.end() + 30], re.I) and m.group(3).lower().startswith("space"):
            if not re.search(r"parking", text[max(0, m.start() - 80):m.end() + 40], re.I):
                continue
        clause = _clause_after(text, m.end(), 45)
        scope = ("per_floor" if re.search(r"per\s+floor|each\s+floor", clause, re.I)
                 else "per_unit" if re.search(r"per\s+(unit|flat|apartment)|each\s+(unit|flat|apartment)", clause, re.I)
                 else "total")
        kind = "allocated" if re.search(r"allocated", m.group(0) + clause, re.I) else "unspecified"
        ctx.add(source, "parking", {"scope": scope}, {"spaces": int(n), "kind": kind}, m.group(0), _line_span(text, m.start(), m.end()))
    for m in re.finditer(r"(total\s+)?(allocated\s+)?parking\s+(?:spaces?|bays?)\s*[:\-]\s*(\d{1,3})", text, re.I):
        kind = "allocated" if m.group(2) else "unspecified"
        ctx.add(source, "parking", {"scope": "total"}, {"spaces": int(m.group(3)), "kind": kind}, m.group(0), _line_span(text, m.start(), m.end()))
    for m in re.finditer(r"\b(single|double|triple)\s+garage\b", text, re.I):
        if re.search(r"\btypes?\b", text[m.end():m.end() + 12], re.I):
            continue
        ctx.add(source, "parking", {"scope": "total"}, {"spaces": WORD_NUMBERS[m.group(1).lower()], "kind": "garage"},
                m.group(0), _line_span(text, m.start(), m.end()), confidence=0.6)


# ---------------------------------------------------------------- secondary fields

def extract_secondary(ctx: Ctx, source: str, text: str):
    for m in re.finditer(rf"\b({COUNT})\s+(?:double\s+)?bed(?:room)?s?\b", text, re.I):
        n = parse_number(m.group(1))
        if n and 0 < n < 20 and not re.search(r"bedrooms?\s*$", text[max(0, m.start() - 10):m.start()], re.I):
            ctx.add(source, "bedrooms", {}, {"count": int(n)}, m.group(0), _line_span(text, m.start(), m.end()), confidence=0.7)
    for m in re.finditer(rf"\b({COUNT})\s+bathrooms?\b", text, re.I):
        n = parse_number(m.group(1))
        if n and n < 20:
            ctx.add(source, "bathrooms", {}, {"count": int(n)}, m.group(0), _line_span(text, m.start(), m.end()), confidence=0.7)
    for m in re.finditer(r"\b(?:listed\s+grade\s+(Il|\|\||II\*?|I)\b|grade\s+(Il|\|\||II\*?|I)\s+listed)", text, re.I):
        grade = (m.group(1) or m.group(2)).replace("Il", "II").replace("||", "II")
        ctx.add(source, "listed_status", {}, {"grade": grade}, m.group(0), _line_span(text, m.start(), m.end()), confidence=0.7)
    for m in re.finditer(r"all\s+en[\s-]?suites\s+(?:are\s+)?(?:fitted\s+with\s+)?([^.]{0,40}?)(showers?|baths?)\b", text, re.I):
        fixture = "shower" if m.group(2).lower().startswith("shower") else "bath"
        ctx.add(source, "bathroom_fixture", {"room": "en_suite_all"}, {"fixture": fixture, "text": m.group(0)}, m.group(0),
                _line_span(text, m.start(), m.end()), scope="development", confidence=0.7)
    for m in re.finditer(r"(principal|guest|master|main)\s+suite[^.]{0,80}?en[\s-]?suite\s+(bathroom|shower\s+room|shower)", text, re.I):
        fixture = "bath" if m.group(2).lower() == "bathroom" else "shower"
        room = f"{m.group(1).lower()}_en_suite"
        ctx.add(source, "bathroom_fixture", {"room": room}, {"fixture": fixture, "text": m.group(0)}, m.group(0),
                _line_span(text, m.start(), m.end()), confidence=0.6)
    for m in re.finditer(rf"to\s+let\W{{1,4}}{FLOOR_RE}", text, re.I):
        ctx.add(source, "availability", {"scope": f"floor:{floor_slug(m.group(1))}"}, {"status": "available"}, m.group(0),
                _line_span(text, m.start(), m.end()), confidence=0.6)
    for m in re.finditer(rf"{FLOOR_RE}[^.]{{0,30}}?\bis\s+(?:currently\s+)?available", text, re.I):
        ctx.add(source, "availability", {"scope": f"floor:{floor_slug(m.group(1))}"}, {"status": "available"}, m.group(0),
                _line_span(text, m.start(), m.end()), confidence=0.6)
    for m in re.finditer(rf"\blease\b[^.]{{0,60}}?\bof\s+the\s+{FLOOR_RE}", text, re.I):
        ctx.add(source, "availability", {"scope": f"floor:{floor_slug(m.group(1))}"}, {"status": "let"}, m.group(0),
                _line_span(text, m.start(), m.end()), confidence=0.6)
    for m in re.finditer(rf"\b({COUNT})\s+floors?\s+remaining\b", text, re.I):
        ctx.add(source, "availability", {"scope": "whole"}, {"status": "available", "text": m.group(0)}, m.group(0),
                _line_span(text, m.start(), m.end()), confidence=0.5)


def extract_type_tables(ctx: Ctx):
    """House-type / plot schedules: per-type bedroom and bathroom counts, attached to the type, never to a plot."""
    rows = [r for r in ctx.page.rows if r.source == "pdf_text"]
    for hi, header in enumerate(rows):
        if not re.fullmatch(r"type|house\s+type", header.words[0].text, re.I):
            continue
        cols = {}
        for w in header.words:
            if re.fullmatch(r"bedrooms?", w.text, re.I):
                cols["bedrooms"] = w.xc
            elif re.fullmatch(r"bathrooms?", w.text, re.I):
                cols["bathrooms"] = w.xc
        if not cols:
            continue
        for row in rows[hi + 1:hi + 20]:
            first = row.words[0].text
            if not re.fullmatch(r"[A-Z]|\d{1,2}[A-Z]?", first) or re.fullmatch(r"plot", first, re.I):
                break
            for field, xc in cols.items():
                best = min((w for w in row.words[1:] if re.fullmatch(r"\d{1,2}", w.text)), key=lambda w: abs(w.xc - xc), default=None)
                if best is not None and abs(best.xc - xc) < 30:
                    ctx.add("pdf_text_table", field, {}, {"count": int(best.text)}, best.text, row.text,
                            target_scope=f"house_type:{first.upper()}", table_header=header.text, confidence=0.85)
    for source, text in ctx.page.sources().items():
        for m in re.finditer(r"\btype\s+([A-Z])\s*:\s*(principal|guest|master)\s+en[\s-]?suite\s+with\s+([^.\n]*)", text, re.I):
            desc = m.group(3).lower()
            fixture = "both" if "bath" in desc and "shower" in desc else "bath" if "bath" in desc else "shower" if "shower" in desc else None
            if fixture:
                ctx.add(source, "bathroom_fixture", {"room": f"{m.group(2).lower()}_en_suite"}, {"fixture": fixture, "text": m.group(0)},
                        m.group(0), _line_span(text, m.start(), m.end()), target_scope=f"house_type:{m.group(1).upper()}", confidence=0.8)


def extract_page(page: Page, doc_type: str, focus_floor: str | None = None) -> list[dict]:
    ctx = Ctx(page, doc_type, focus_floor)
    for source, text in page.sources().items():
        for fn in (extract_money, extract_tenure, extract_area, extract_epc, extract_parking, extract_secondary):
            fn(ctx, source, text)
    extract_area_tables(ctx)
    extract_type_tables(ctx)
    return ctx.out
