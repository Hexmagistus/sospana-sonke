"""African employers outside South Africa, from university lists and company lists.

Greenhouse, Lever, Ashby and SmartRecruiters were probed. None of those boards
had a majority of located roles in the headquarters country, so every row from
this list is a blank. South Africa is unchanged.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 africa-employers'
BLANK = {
    ('Egypt', 'UNI'): 44,
    ('Ghana', 'UNI'): 46,
    ('Kenya', 'UNI'): 27,
    ('Morocco', 'PRIVATE'): 61,
    ('Morocco', 'UNI'): 12,
    ('Nigeria', 'UNI'): 140,
}
LINKED_TOTAL = {
    'Nigeria': 93,
    'Kenya': 133,
    'Egypt': 34,
    'Morocco': 13,
    'Ghana': 57,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_africa_employers_follow_the_blank_link_rule():
    added = [row for row in _rows() if row["relevance_note"].startswith(NOTE)]
    assert len(added) == sum(BLANK.values())
    assert not any(row["country"] == "South Africa" for row in added)
    blank = {key: 0 for key in BLANK}
    names = []
    for row in added:
        names.append((row["company_name"].casefold(), row["country"].casefold()))
        assert row["careers_url"] == ""
        assert row["active"] == "false"
        assert row["careers_status"] == "grey_none_verified"
        assert row["scraping_status"] == "no_url"
        assert row["jse_code"] == ""
        assert row["official_website"] == ""
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        blank[(row["country"], row["source_type"])] += 1
    assert blank == BLANK
    assert len(names) == len(set(names))


def test_africa_employer_link_counts_and_south_africa_is_untouched():
    counts = {country: 0 for country in LINKED_TOTAL}
    sa = 0
    for row in _rows():
        if row["country"] == "South Africa" and row["active"] == "true" and row["careers_url"].strip():
            sa += 1
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
    assert sa == 815
