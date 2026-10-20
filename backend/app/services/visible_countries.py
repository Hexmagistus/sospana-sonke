"""Countries the site shows (reversible focus filter, Oct 2026).

Kept: every country with English as an official language (list below, based on the
"List of countries and territories where English is an official language"), every SADC
member and every BRICS member, plus the Africa / International directory buckets.
Everything else is HIDDEN from public lists, counts and jobs, never deleted: rows stay in
the seed files and the database.

Undo: set env HIDE_NON_ENGLISH_COUNTRIES=0 on the API (and NEXT_PUBLIC_HIDE_NON_ENGLISH_COUNTRIES=0
on the frontend, see frontend/src/lib/visibleCountries.ts). Keep both lists identical.
"""
from __future__ import annotations

import os

from sqlalchemy import or_, true

from app.services.country_names import NON_COUNTRY_BUCKETS, canonical_country, spellings_for

SADC = frozenset({
    "South Africa", "Angola", "Botswana", "Comoros", "DR Congo", "Eswatini", "Lesotho", "Madagascar",
    "Malawi", "Mauritius", "Mozambique", "Namibia", "Seychelles", "Tanzania", "Zambia", "Zimbabwe",
})
BRICS = frozenset({
    "Brazil", "Russia", "India", "China", "South Africa", "Egypt", "Ethiopia", "Iran",
    "United Arab Emirates", "Indonesia",
})
# English is an official (de jure or de facto national) language.
ENGLISH_OFFICIAL = frozenset({
    # Africa
    "South Africa", "Botswana", "Burundi", "Cameroon", "Eswatini", "Gambia", "Ghana", "Kenya", "Lesotho",
    "Liberia", "Malawi", "Mauritius", "Namibia", "Nigeria", "Rwanda", "Seychelles", "Sierra Leone",
    "South Sudan", "Sudan", "Tanzania", "Uganda", "Zambia", "Zimbabwe", "Saint Helena",
    # Europe
    "United Kingdom", "Ireland", "Malta", "Gibraltar",
    # Americas & Caribbean
    "United States", "Canada", "Antigua and Barbuda", "Bahamas", "Barbados", "Belize", "Dominica",
    "Grenada", "Guyana", "Jamaica", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Trinidad and Tobago", "Anguilla", "Bermuda",
    "British Virgin Islands", "Cayman Islands", "Montserrat", "Turks and Caicos Islands",
    "US Virgin Islands", "Puerto Rico", "Falkland Islands", "Sint Maarten", "Curaçao",
    "Caribbean Netherlands",
    # Asia
    "India", "Pakistan", "Philippines", "Singapore", "Hong Kong",
    # Oceania
    "Australia", "New Zealand", "Fiji", "Papua New Guinea", "Samoa", "Tonga", "Solomon Islands",
    "Vanuatu", "Kiribati", "Marshall Islands", "Micronesia", "Nauru", "Palau", "Tuvalu",
    "Cook Islands", "Niue", "American Samoa", "Guam", "Northern Mariana Islands",
})
VISIBLE_COUNTRIES = SADC | BRICS | ENGLISH_OFFICIAL | NON_COUNTRY_BUCKETS


def hiding_enabled() -> bool:
    return os.environ.get("HIDE_NON_ENGLISH_COUNTRIES", "1").strip().lower() not in {"0", "false", "no", "off"}


def is_visible_country(name: str | None) -> bool:
    """Blank/unknown country rows are never hidden."""
    if not hiding_enabled() or not name or not name.strip():
        return True
    return canonical_country(name) in VISIBLE_COUNTRIES


_SPELLINGS = sorted({s for c in VISIBLE_COUNTRIES for s in spellings_for(c)})


def visible_country_clause(column):
    """SQL filter: column is a visible country, or blank. `true()` when hiding is off."""
    if not hiding_enabled():
        return true()
    return or_(column.is_(None), column == "", column.in_(_SPELLINGS))
