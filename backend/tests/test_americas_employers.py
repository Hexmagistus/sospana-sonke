"""Canada and Latin America employers added from market indexes and universities.

Greenhouse, Lever, Ashby and SmartRecruiters were probed. None of those boards
had a majority of located roles in the headquarters country, so every row from
this list is a blank.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 americas-employers'
BLANK = {
    ('Argentina', 'MUNI'): 1,
    ('Argentina', 'UNI'): 1,
    ('Brazil', 'MUNI'): 1,
    ('Brazil', 'UNI'): 1,
    ('Canada', 'COLLEGE'): 1,
    ('Canada', 'DEPT'): 1,
    ('Canada', 'HOSPITAL'): 1,
    ('Canada', 'MUNI'): 1,
    ('Canada', 'NGO'): 1,
    ('Canada', 'PRIVATE'): 59,
    ('Canada', 'SOE'): 1,
    ('Canada', 'UNI'): 92,
    ('Colombia', 'PRIVATE'): 15,
    ('Ecuador', 'PRIVATE'): 9,
    ('Ecuador', 'UNI'): 1,
    ('Mexico', 'HOSPITAL'): 1,
    ('Mexico', 'MUNI'): 1,
    ('Mexico', 'PRIVATE'): 32,
    ('Mexico', 'UNI'): 2,
    ('Uruguay', 'PRIVATE'): 4,
    ('Uruguay', 'UNI'): 1,
}
LINKED_TOTAL = {
    'Canada': 10,
    'Mexico': 3,
    'Brazil': 435,
    'Argentina': 82,
    'Colombia': 21,
    'Uruguay': 6,
    'Ecuador': 2,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_americas_employers_follow_the_blank_link_rule():
    added = [row for row in _rows() if row["relevance_note"].startswith(NOTE)]
    assert len(added) == sum(BLANK.values())
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


def test_americas_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
