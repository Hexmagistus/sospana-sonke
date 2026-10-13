"""Official South African unemployment rates copied from one Stats SA table.

The file is the store. Figures are the published one-decimal rates, with the
decimal comma kept so a later edit cannot silently re-round them. Nothing
here estimates a rate the table does not print.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "data" / "sa_qlfs_table_e.json"
_LATEST = -1


class LabourTableError(ValueError):
    pass


def _check(data: dict) -> dict:
    periods = data.get("periods") or []
    rows = data.get("rows") or []
    if len(periods) < 1 or len(rows) != 10:
        raise LabourTableError("the labour table needs its periods and ten places")
    width = len(periods)
    places = [row.get("place") for row in rows]
    if places[0] != "South Africa" or len(set(places)) != 10:
        raise LabourTableError("the labour table places are incomplete")
    for row in rows:
        for key in ("official", "expanded"):
            values = row.get(key) or []
            if len(values) != width:
                raise LabourTableError(f"{row.get('place')} is missing a {key} rate")
            for value in values:
                if not isinstance(value, str) or "," not in value:
                    raise LabourTableError(f"{row.get('place')} has a rate that is not the published comma form")
    if "sold" not in (data.get("licence") or "") or "acknowledged" not in (data.get("licence") or ""):
        raise LabourTableError("the labour table is missing the Stats SA reuse terms")
    if data.get("download_permitted") is not False:
        raise LabourTableError("a download is not part of this release")
    return data


@lru_cache(maxsize=1)
def load_table() -> dict | None:
    """The stored table, or None when the file is absent."""
    if not _PATH.is_file():
        return None
    return _check(json.loads(_PATH.read_text(encoding="utf-8")))


def clear_table_cache() -> None:
    load_table.cache_clear()


def place_row(place: str) -> dict | None:
    table = load_table()
    if table is None:
        return None
    for row in table["rows"]:
        if row["place"].lower() == place.lower():
            return row
    return None


def latest_rate(row: dict, series: str) -> str:
    return row[series][_LATEST]


def public_document() -> dict:
    """The whole table for the data page. `loaded` is false when the file is missing."""
    table = load_table()
    if table is None:
        return {"loaded": False}
    return {"loaded": True, **table}
