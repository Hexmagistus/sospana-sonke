"""Read an employer's own closing date out of a vacancy page's text.

Only a date that follows an explicit closing label counts ("Closing date:",
"Applications close on", "Deadline"). The label has to be a whole word, in the
same sentence as the date. A date with no such label, an opening or posting
date, a date in the next sentence, and a date that cannot be parsed are all
ignored, so the function returns None rather than guess. Nothing is invented.
"""
from __future__ import annotations

import re
from datetime import date

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_MON = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

# 20 November 2026 / 20th Nov 2026 / 20 Nov, 2026
_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s\-/.,]+(?:of\s+)?({_MON})\.?[\s\-/.,]+(\d{{4}})\b", re.I)
# November 20, 2026 / Nov 20th 2026
_MDY = re.compile(rf"\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I)
# 2026-11-20 / 2026/11/20
_YMD = re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b")
# 20/11/2026 / 20-11-2026 (South African day-first order)
_DMY_NUM = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b")

# Whole words only, so "enclose", "disclosure" and "weekend date" are not labels.
_LABEL = re.compile(
    r"\b(?:closing\s*(?:date|time)?|close\s*date|closes?(?:\s+on)?|deadline|"
    r"applications?\s+(?:close|closes|closing|must\s+(?:be\s+)?(?:submitted|received|reach)|should\s+(?:be\s+)?(?:submitted|received|reach)|"
    r"will\s+close|are\s+to\s+be\s+(?:submitted|received))|"
    r"last\s+date\s+(?:to|for)\s+(?:apply|application)s?|apply\s+(?:by|before)|"
    r"submit(?:ted)?\s+(?:by|before|on\s+or\s+before)|end\s+date)\b",
    re.I,
)
_WINDOW = 90
_SENTENCE_BREAK = re.compile(r"[.!?](?=\s)")


def _month_number(token: str) -> int | None:
    return _MONTHS.get(token.lower().rstrip("."))


def _valid(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _named(year: int, month_token: str, day: int) -> date | None:
    month = _month_number(month_token)
    if month is None:
        return None
    return _valid(year, month, day)


def _same_sentence(fragment: str) -> str:
    """Drop the next sentence. Keep a period that belongs to a month ("Nov.")."""
    for match in _SENTENCE_BREAK.finditer(fragment):
        if match.group() == ".":
            word = re.search(r"([A-Za-z]+)$", fragment[: match.start()])
            if word and word.group(1).lower() in _MONTHS:
                continue
        return fragment[: match.start()]
    return fragment


def parse_date_near_start(fragment: str) -> date | None:
    """First date that appears at the start of ``fragment`` (after filler words)."""
    best: tuple[int, date] | None = None
    for rx, build in (
        (_DMY, lambda m: _named(int(m.group(3)), m.group(2), int(m.group(1)))),
        (_MDY, lambda m: _named(int(m.group(3)), m.group(1), int(m.group(2)))),
        (_YMD, lambda m: _valid(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (_DMY_NUM, lambda m: _valid(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
    ):
        m = rx.search(fragment)
        if not m:
            continue
        found = build(m)
        if found is None:
            continue
        if best is None or m.start() < best[0]:
            best = (m.start(), found)
    return best[1] if best else None


def extract_closing_date(text: str | None, *, earliest_year: int = 2025) -> date | None:
    """The date named by the first closing-date label in ``text``, or None."""
    if not text:
        return None
    flat = re.sub(r"\s+", " ", text)
    for label in _LABEL.finditer(flat):
        tail = _same_sentence(flat[label.end(): label.end() + _WINDOW])
        found = parse_date_near_start(tail)
        if found and found.year >= earliest_year:
            return found
    return None
