"""Middle East employers added from exchange lists and universities.

Greenhouse, Lever, Ashby and SmartRecruiters were probed. None of those boards
had a majority of located roles in the headquarters country, so every row from
this list is a blank.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 mena-employers'
BLANK = {
    ('Israel', 'DEPT'): 1,
    ('Israel', 'HOSPITAL'): 1,
    ('Israel', 'MUNI'): 1,
    ('Israel', 'NGO'): 1,
    ('Israel', 'PRIVATE'): 51,
    ('Israel', 'UNI'): 67,
    ('Qatar', 'DEPT'): 1,
    ('Qatar', 'NGO'): 1,
    ('Qatar', 'PRIVATE'): 27,
    ('Qatar', 'UNI'): 10,
    ('Saudi Arabia', 'DEPT'): 1,
    ('Saudi Arabia', 'HOSPITAL'): 1,
    ('Saudi Arabia', 'MUNI'): 1,
    ('Saudi Arabia', 'PRIVATE'): 95,
    ('Saudi Arabia', 'UNI'): 53,
    ('United Arab Emirates', 'DEPT'): 1,
    ('United Arab Emirates', 'PRIVATE'): 109,
    ('United Arab Emirates', 'UNI'): 52,
}
LINKED_TOTAL = {
    'United Arab Emirates': 21,
    'Saudi Arabia': 4,
    'Qatar': 6,
    'Israel': 9,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_mena_employers_follow_the_blank_link_rule():
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


def test_mena_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
