"""Detect and repair text layers whose font encoding shifts every code point by a constant.

Strutt & Parker's No. 59 brochure is the reference case: some lines come out shifted by -29
("(OHJDQW" is "Elegant"), spaces vanish, and ligature glyphs map to stray Latin-1 letters.
"""
from __future__ import annotations

import re

COMMON_TRIGRAMS = (
    "the", "and", "ing", "ion", "ent", "her", "for", "tha", "nth", "int", "ere", "tio", "ter", "est",
    "ers", "ati", "hat", "ate", "all", "eth", "hes", "ver", "his", "oft", "ith", "res", "ont", "ous",
    "roo", "oom", "wit", "pro", "ers", "are", "con", "ted", "com", "nce", "edr", "bed",
)
COMMON_WORDS = {
    "the", "and", "of", "to", "a", "in", "with", "is", "for", "on", "as", "by", "be", "are", "this",
    "or", "at", "from", "an", "it", "that", "which", "all", "has", "have", "not", "room", "floor",
}
# Ligature glyphs seen in shifted text, with their real meaning.
LIGATURES = {"Ć": "fi", "ć": "fl", "ê": "\u201c", "ë": "\u201d"}


def english_score(text: str) -> float:
    letters = re.sub(r"[^a-z]", "", text.lower())
    if len(letters) < 6:
        return 0.0
    hits = sum(letters.count(t) for t in COMMON_TRIGRAMS)
    # Shifts that differ by 32 only flip ASCII case; prefer the mostly-lowercase reading.
    lower = sum(c.islower() for c in text) / max(1, sum(c.isalpha() for c in text))
    return hits / len(letters) + 0.01 * lower


def _shift(text: str, k: int) -> str:
    out = []
    for ch in text:
        if ch in LIGATURES:
            out.append(LIGATURES[ch])
            continue
        c = ord(ch) + k
        out.append(chr(c) if 32 <= c < 127 else ("" if c < 32 else ch))
    return "".join(out)


def best_shift(line: str) -> tuple[int, float]:
    base = english_score(line)
    best = (0, base)
    for k in range(-40, 41):
        if k == 0:
            continue
        s = english_score(_shift(line, k))
        if s > best[1]:
            best = (k, s)
    return best


def is_garbled_line(line: str) -> tuple[bool, int]:
    stripped = line.strip()
    if len(re.sub(r"\s", "", stripped)) < 20:
        return False, 0
    # The broken encoding maps the space glyph below 0x20, so garbled runs have almost no spaces.
    if stripped.count(" ") / len(stripped) > 0.05:
        return False, 0
    words = re.findall(r"[a-z]+", stripped.lower())
    if sum(w in COMMON_WORDS for w in words) >= 2:
        return False, 0
    k, score = best_shift(stripped)
    base = english_score(stripped)
    if k != 0 and score >= 0.07 and score > 2.5 * base + 0.02:
        return True, k
    return False, 0


def analyse(text: str) -> dict:
    """Return garbled-line stats and a repaired copy of the text."""
    lines = text.splitlines()
    garbled_chars = total_chars = 0
    shifts: dict[int, int] = {}
    repaired = []
    for line in lines:
        n = len(line.strip())
        total_chars += n
        bad, k = is_garbled_line(line)
        if bad:
            garbled_chars += n
            shifts[k] = shifts.get(k, 0) + 1
            repaired.append(_shift(line.strip(), k))
        else:
            repaired.append(line)
    ratio = garbled_chars / total_chars if total_chars else 0.0
    return {
        "garbled_ratio": round(ratio, 3),
        "garbled_lines": sum(shifts.values()),
        "shift": max(shifts, key=shifts.get) if shifts else 0,
        "repaired_text": "\n".join(repaired),
    }
