"""One spelling per country, matching the homepage LIVE list exactly.

Production rows were imported under several spellings of the same country
(accented São Tomé, "Ivory Coast", "Cape Verde", "Republic of Congo"). The
homepage overlays `/companies/stats` `by_country` by exact string, so a second
spelling is a second country. `International` and `Africa` are real directory
rows (continental bodies) and stay in the employer total; they are not countries.
"""
from __future__ import annotations

import unicodedata

# Canonical values are the homepage strings. Do not map DR Congo onto Congo.
COUNTRY_ALIASES: dict[str, str] = {
    "São Tomé and Príncipe": "Sao Tome and Principe",
    "São Tomé and Principe": "Sao Tome and Principe",
    "Sao Tome and Príncipe": "Sao Tome and Principe",
    "Cote dIvoire": "Côte d'Ivoire",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Cote d’Ivoire": "Côte d'Ivoire",
    "Côte d’Ivoire": "Côte d'Ivoire",
    "Ivory Coast": "Côte d'Ivoire",
    "Cape Verde": "Cabo Verde",
    "Republic of Congo": "Congo",
    "Republic of the Congo": "Congo",
}

# Directory buckets that are not a country. Kept in by_country so employer
# totals still add up; omitted from the country count.
NON_COUNTRY_BUCKETS = frozenset({"International", "Africa"})


def canonical_country(name: str | None) -> str:
    """Return the homepage spelling. Unknown names pass through, stripped."""
    if not name:
        return ""
    stripped = unicodedata.normalize("NFC", name.strip())
    return COUNTRY_ALIASES.get(stripped, stripped)


def spellings_for(name: str | None) -> list[str]:
    """Canonical name plus every alias that maps to it, for filters."""
    canon = canonical_country(name)
    if not canon:
        return []
    found = {canon}
    for alias, target in COUNTRY_ALIASES.items():
        if target == canon:
            found.add(alias)
    return sorted(found)


def is_country(name: str | None) -> bool:
    canon = canonical_country(name)
    return bool(canon) and canon not in NON_COUNTRY_BUCKETS
