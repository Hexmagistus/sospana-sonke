"""Explorer page groups: which ``companies.source_type`` values each page lists.

The directory stores one category per row in ``companies.source_type``, a short
upper-case code (UNI, NGO, DEPT, ...). The column is ``String(10)`` and the CSV
import stores ``value.strip().upper()[:10]``, so a human label such as
"TVET College" lands as ``TVET COLLE``.

Each explorer page lists one group of canonical codes. ``ALIASES`` lets a row
stored under another sensible label (Government, Municipality, NPO, TVET
College, Parastatal, ...) land on the right page under the right canonical
code without any data change. To support a new label, add one line to
``ALIASES`` (and the same line to the frontend mirror); the tests check that
the two files agree and that no label points at two codes.

This is the single server-side source of truth; the frontend mirrors it in
``frontend/src/lib/explorer/categoryGroups.ts``.

Nothing is stored or migrated: a group is only a filter over existing values, so
a row keeps its own value and still shows under its code on /companies too
(state-owned entities stay findable under "State-owned" there).
"""
from __future__ import annotations

# companies.source_type is String(10); the CSV import cuts values to this length.
STORED_LENGTH = 10

CATEGORY_GROUPS: dict[str, tuple[str, ...]] = {
    # /universities
    "universities": ("UNI",),
    # /colleges: TVET, public and private colleges, and the SETAs.
    "colleges": ("COLLEGE", "SETA"),
    # /hospitals
    "hospitals": ("HOSPITAL",),
    # /ngos: NGOs, charities, non-profits and international / UN organisations.
    "ngos": ("NGO",),
    # /government: national and provincial departments, municipalities and
    # metros, and state-owned entities / public agencies.
    "government": ("DEPT", "MUNI", "SOE"),
}

# Other labels a row may be stored under -> the canonical code it is listed as.
# Written as people would type them; matching uses the stored form (stored_code).
ALIASES: dict[str, str] = {
    # colleges
    "TVET": "COLLEGE",
    "TVET College": "COLLEGE",
    "Private College": "COLLEGE",
    "Public College": "COLLEGE",
    # ngos
    "NPO": "NGO",
    "NPC": "NGO",
    "Non-profit": "NGO",
    "Nonprofit": "NGO",
    "Charity": "NGO",
    "INGO": "NGO",
    "UN": "NGO",
    "Intl Org": "NGO",
    "IGO": "NGO",
    # government
    "Government": "DEPT",
    "Govt": "DEPT",
    "Department": "DEPT",
    "Ministry": "DEPT",
    "Provincial": "DEPT",
    "Municipality": "MUNI",
    "Metro": "MUNI",
    "Local Govt": "MUNI",
    "State-owned": "SOE",
    "Parastatal": "SOE",
    "Public Entity": "SOE",
    "Public Agency": "SOE",
}


def stored_code(value: str | None) -> str:
    """How a category label is stored in companies.source_type (upper-case, 10 chars)."""
    return (value or "").strip().upper()[:STORED_LENGTH]


_CANONICAL = {code for codes in CATEGORY_GROUPS.values() for code in codes}
_ALIAS_TO_CODE: dict[str, str] = {stored_code(k): v for k, v in ALIASES.items()}


def canonical_type(value: str | None) -> str:
    """The canonical code for a stored value: an alias maps to its code, anything else is unchanged."""
    key = stored_code(value)
    return _ALIAS_TO_CODE.get(key, key)


def stored_values_for(code: str | None) -> tuple[str, ...]:
    """Every stored value listed under one category code: the code itself plus its aliases."""
    c = canonical_type(code)
    if not c:
        return ()
    return (c, *sorted(k for k, v in _ALIAS_TO_CODE.items() if v == c and k != c))


def types_for_group(name: str | None) -> tuple[str, ...] | None:
    """The stored source_type values a group lists (case-insensitive name), or None if unknown."""
    if not name:
        return None
    codes = CATEGORY_GROUPS.get(name.strip().lower())
    if codes is None:
        return None
    return tuple(v for code in codes for v in stored_values_for(code))


def group_of(value: str | None) -> str | None:
    """The group a stored value is listed in, or None (e.g. JSE, PRIVATE: /companies only)."""
    code = canonical_type(value)
    for group, codes in CATEGORY_GROUPS.items():
        if code in codes:
            return group
    return None
