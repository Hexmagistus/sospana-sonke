"""Decide whether a public board is this employer's own in-country list.

Used by the offline discovery script. A majority of located roles in the
employer's country accepts the board URL. Fewer than half still accepts a
stable country filter when that filter itself lists at least two roles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.services.seed_locations import tally_locations

MIN_ROLES = 2
MIN_SHARE = 0.5

_STOP = {
    "inc", "incorporated", "corp", "corporation", "plc", "ltd", "limited", "llc",
    "lp", "company", "co", "group", "holdings", "holding", "the", "of", "and",
    "for", "nhs", "foundation", "trust", "university", "hospitals", "hospital",
    "health", "system", "systems", "services", "service", "international",
    "national", "american", "british", "united", "states", "kingdom", "city",
    "council", "department", "ministry", "jobs", "career", "careers", "bank",
    "energy", "capital", "global", "financial", "partners", "partner",
}
_GENERIC_EXTRA = {
    "group", "holdings", "holding", "international", "intl", "plc", "limited",
    "inc", "corp", "company", "co", "uk", "usa",
}
_GENERIC_SLUG = _STOP | {
    "public", "flex", "applied", "parker", "mosaic", "quanta", "constellation",
    "waterworks", "digital", "first", "general", "royal", "standard",
}
# Named large-cap lists and large hospital systems. A row is a large group only
# when its note names one of these. AIM, local "companies" lists, universities,
# municipalities, and NHS trusts are not in this set.
_LARGE_GROUP_LABELS = {
    "S&P 500", "FTSE 100", "FTSE 250", "Nikkei 225", "KOSPI 200", "ASX 200",
    "SDAX", "MDAX", "DAX", "S&P/TSX 60", "Dubai Financial Market", "TA-125",
    "SET50", "NZX 50", "Nifty Next 50", "Nifty 50", "BSE Sensex", "LQ45",
    "CAC 40", "IPC", "FTSE MIB", "Straits Times", "IBEX 35", "PSEi", "WIG30",
    "FBM KLCI", "OMX Stockholm 30", "OMX Helsinki 25", "OBX", "SMIM",
    "OMX Copenhagen 25", "SMI", "AMX", "AEX", "COLCAP", "Icelandic banks",
    "ISEQ 20", "major companies", "US hospital systems",
}
_FACET_ID = re.compile(r"^[a-f0-9]{16,40}$", re.I)
_DESCRIPTORS = {
    "United States": {"united states", "united states of america", "usa"},
    "United Kingdom": {"united kingdom", "great britain", "uk"},
    "Germany": {"germany", "deutschland"},
    "France": {"france"},
    "Netherlands": {"netherlands", "the netherlands", "holland"},
    "Ireland": {"ireland"},
    "Norway": {"norway"},
    "Sweden": {"sweden"},
    "Denmark": {"denmark"},
    "Finland": {"finland"},
    "Iceland": {"iceland"},
    "Spain": {"spain"},
    "Italy": {"italy", "italia"},
    "Switzerland": {"switzerland"},
    "Poland": {"poland"},
    "Japan": {"japan"},
    "South Korea": {"south korea", "korea, republic of", "republic of korea"},
    "Canada": {"canada"},
    "United Arab Emirates": {"united arab emirates", "uae"},
    "Saudi Arabia": {"saudi arabia"},
    "Qatar": {"qatar"},
    "Israel": {"israel"},
    "Nigeria": {"nigeria"},
    "Kenya": {"kenya"},
    "Egypt": {"egypt"},
    "Morocco": {"morocco"},
    "Ghana": {"ghana"},
    "South Africa": {"south africa"},
    "Australia": {"australia"},
    "India": {"india"},
    "Singapore": {"singapore"},
    "Malawi": {"malawi"},
}


@dataclass(frozen=True)
class BoardDecision:
    """``filtered`` is true only when the unfiltered board is too global."""

    accept: bool
    filtered: bool
    here: int
    located: int
    share: float


def decide_board(locations: list[str], country: str) -> BoardDecision:
    here, located, share = tally_locations(locations, country)
    return _from_counts(here, located, share)


def decide_counts(here: int, located: int) -> BoardDecision:
    share = (here / located) if located else 0.0
    return _from_counts(here, located, share)


def _from_counts(here: int, located: int, share: float) -> BoardDecision:
    if here >= MIN_ROLES and located and share >= MIN_SHARE:
        return BoardDecision(True, False, here, located, share)
    if here >= MIN_ROLES:
        return BoardDecision(True, True, here, located, share)
    return BoardDecision(False, False, here, located, share)


def is_large_group(source_type: str, note: str) -> bool:
    """True for a listed large-cap employer or a named large hospital system.

    Small and local employers stay on the strict in-country rule. The marker
    is the list name in the seed note, not a guess from the company name.
    """
    kind = (source_type or "").strip().upper()
    if kind not in {"PRIVATE", "HOSPITAL"}:
        return False
    text = note or ""
    if ":" not in text:
        return False
    label = text.split(":", 1)[1].split(".", 1)[0].strip()
    return label in _LARGE_GROUP_LABELS


def core_words(name: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", name.lower().replace("&", " and "))
    kept = [word for word in words if word not in _STOP and len(word) >= 2]
    if not kept:
        kept = [word for word in words if len(word) >= 2]
    return kept


def names_match(candidate: str, board: str) -> bool:
    """True when the board's own name is this employer, not a neighbour."""
    if not board:
        return False
    candidate_words, board_words = core_words(candidate), core_words(board)
    if not candidate_words or not board_words:
        left = re.sub(r"[^a-z0-9]", "", candidate.lower())
        right = re.sub(r"[^a-z0-9]", "", board.lower())
        return len(left) >= 2 and (left == right or left in right or right in left)
    if candidate_words == board_words:
        return True
    if len(board_words) < len(candidate_words) and candidate_words[:len(board_words)] == board_words and len(board_words[0]) >= 4:
        return True
    if (
        len(candidate_words) < len(board_words)
        and board_words[:len(candidate_words)] == candidate_words
        and all(word in _GENERIC_EXTRA for word in board_words[len(candidate_words):])
    ):
        return True
    return False


def ats_slug(url: str) -> str:
    """The board token on a careers URL.

    A Workday URL keeps the tenant in the host (``allegion.wd5``) and the site
    name in the path (``Careers``). Other public boards keep the token in the
    first path segment.
    """
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(".myworkdayjobs.com"):
        return host.split(".")[0]
    parts = [part for part in urlparse(url).path.split("/") if part]
    return (parts[0] if parts else "").replace("-", "").lower()


def slug_is_reliable(name: str, url: str) -> bool:
    """True when the board token is this employer's name, not a short neighbour.

    ``arch`` matches Arch Capital Group only after ``capital`` and ``group``
    are ignored, and ``universal`` matches Universal Health Services only
    after ``health`` and ``services`` are ignored. Those tokens are rejected.
    ``abbott`` still fits Abbott Laboratories, and a full compact name such
    as ``analogdevices`` is kept.
    """
    token = ats_slug(url)
    if not tenant_fits(name, token):
        return False
    raw = re.findall(r"[a-z0-9]+", (name or "").lower().replace("&", " and "))
    raw = [word for word in raw if word not in _LEGAL_SUFFIX and len(word) >= 2]
    words = core_words(name)
    compact = "".join(words)
    full = "".join(raw)
    dropped = [word for word in raw if word not in words]
    # ``universal`` matches Universal Health Services only because health and
    # services were ignored. The token has to carry those words, or be a
    # generic suffix on an otherwise complete name (Abbott Laboratories).
    if dropped and token != full:
        return False
    if token == compact and dropped and len(token) < 8:
        return False
    if words and token == words[0] and token != compact and len(token) < 6:
        return False
    return True


_LEGAL_SUFFIX = {
    "inc", "incorporated", "corp", "corporation", "plc", "ltd", "limited",
    "llc", "lp", "company", "co", "the",
}


def tenant_fits(name: str, slug: str) -> bool:
    """True when a Workday tenant is this employer, not a shorter neighbour.

    ``williams`` is the Williams board, not Williams-Sonoma. ``abbott`` still
    fits Abbott Laboratories, because the leftover word is a generic suffix.
    """
    words = core_words(name)
    compact = "".join(words)
    token = (slug or "").replace("-", "").lower()
    if len(token) < 4 or not compact:
        return False
    if token == compact:
        return True
    if words and token == words[0]:
        return all(word in _GENERIC_EXTRA or word in _STOP or word in {"laboratories", "laboratory", "labs"} for word in words[1:])
    return False


def slug_variants(name: str) -> list[str]:
    """A few public-board tokens derived from the employer's name."""
    raw = name.lower().replace("&", " and ").replace("'", "").replace("’", "")
    raw = re.sub(r"\(.*?\)", " ", raw)
    words = re.findall(r"[a-z0-9]+", raw)
    legal = {"inc", "incorporated", "corp", "corporation", "plc", "ltd", "limited", "llc", "lp", "company", "co", "the"}
    full_words = [word for word in words if word not in legal]
    core = [word for word in full_words if word not in _STOP]
    sequences = []
    if full_words:
        sequences.append(full_words)
    if core and core != full_words:
        sequences.append(core)
    if core and len(core[0]) >= 4:
        sequences.append([core[0]])
    out: list[str] = []
    for sequence in sequences:
        for slug in ("".join(sequence), "-".join(sequence)):
            compact = slug.replace("-", "")
            if len(slug) < 4 or compact in _GENERIC_SLUG or slug in out:
                continue
            out.append(slug)
            if len(out) >= 4:
                return out
    return out


# Workday names this facet one of two ways. The public jobs POST has to send
# the same key the board published, or it answers 400 and the filter is ignored.
_COUNTRY_PARAMS = ("locationCountry", "Location_Country")


def workday_country_facet(payload: dict, country: str) -> tuple[str, str, int, int] | None:
    """Return ``(facet parameter, facet id, in-country count, all-country count)``.

    The country facet is often nested under the locations group, and some boards
    publish it as ``Location_Country`` rather than ``locationCountry``. Absent
    facet returns None so the caller can fall back to the posting locations.
    """
    wanted = _DESCRIPTORS.get(country)
    if not wanted:
        return None
    grouped: dict[str, list] = {name: [] for name in _COUNTRY_PARAMS}
    for facet in _iter_facets(payload.get("facets") or []):
        param = facet.get("facetParameter") or ""
        if param in grouped:
            grouped[param].append(facet)
    for param in _COUNTRY_PARAMS:
        found = _facet_match(grouped[param], wanted)
        if found is not None:
            facet_id, here, located = found
            return param, facet_id, here, located
    return None


def _facet_match(facets: list, wanted: set[str]) -> tuple[str, int, int] | None:
    best_id = ""
    best_count = -1
    here = 0
    located = 0
    saw = False
    for facet in facets:
        for value in facet.get("values") or []:
            if not isinstance(value, dict):
                continue
            saw = True
            count = int(value.get("count") or 0)
            located += count
            descriptor = (value.get("descriptor") or "").strip().lower()
            ident = str(value.get("id") or "")
            if descriptor in wanted and _FACET_ID.fullmatch(ident):
                here += count
                if count > best_count:
                    best_id = ident
                    best_count = count
    if not saw or not best_id:
        return None
    return best_id, here, located


def _iter_facets(node):
    if isinstance(node, dict):
        if node.get("facetParameter"):
            yield node
        for value in node.get("values") or []:
            yield from _iter_facets(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_facets(item)


def workday_filter_url(page_url: str, facet_id: str, parameter: str = "locationCountry") -> str:
    """Stable Workday URL that asks the board for one country."""
    if parameter not in _COUNTRY_PARAMS:
        raise ValueError("facet parameter")
    if not _FACET_ID.fullmatch(facet_id or ""):
        raise ValueError("facet id")
    parsed = urlparse(page_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in _COUNTRY_PARAMS
    ]
    query.append((parameter, facet_id))
    return urlunparse(parsed._replace(query=urlencode(query), fragment=""))
