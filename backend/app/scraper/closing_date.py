"""Read an employer's own closing date out of a vacancy page's text.

Only a date that follows an explicit closing label counts ("Closing date:",
"Applications close on", "Deadline"). A date with no such label, an opening
or posting date, and a date that cannot be parsed are all ignored, so the
function returns None rather than guess. Nothing is invented.
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

_LABEL = re.compile(
    r"(?:closing\s*(?:date|time)?|close\s*date|closes?(?:\s+on)?|deadline|"
    r"applications?\s+(?:close|closes|closing|must\s+(?:be\s+)?(?:submitted|received|reach)|should\s+(?:be\s+)?(?:submitted|received|reach)|"
    r"will\s+close|are\s+to\s+be\s+(?:submitted|received))|"
    r"last\s+date\s+(?:to|for)\s+(?:apply|application)s?|apply\s+(?:by|before)|"
    r"submit(?:ted)?\s+(?:by|before|on\s+or\s+before)|end\s+date)",
    re.I,
)
_WINDOW = 90


def _valid(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_date_near_start(fragment: str) -> date | None:
    """First date that appears at the start of ``fragment`` (after filler words)."""
    best: tuple[int, date] | None = None
    for rx, build in (
        (_DMY, lambda m: _valid(int(m.group(3)), _MONTHS[m.group(2).lower().rstrip('.')], int(m.group(1)))),
        (_MDY, lambda m: _valid(int(m.group(3)), _MONTHS[m.group(1).lower().rstrip('.')], int(m.group(2)))),
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
        tail = flat[label.end(): label.end() + _WINDOW]
        # stop at a sentence/line cut that clearly starts something else
        found = parse_date_near_start(tail)
        if found and found.year >= earliest_year:
            return found
    return None
