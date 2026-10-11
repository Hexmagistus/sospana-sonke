"""Middle East employers added from exchange lists and universities.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, and the page is that
employer's own careers board. Liveperson and NICE are large groups whose own
board is global. Those rows are `global_group` and the note contains
`careers_scope=global`. Everyone else from the same lists is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 mena-employers'
LINKS = {
    'Liveperson Inc.': ('Israel', 'https://job-boards.greenhouse.io/liveperson', 'PRIVATE', 'greenhouse'),
    'NICE Ltd.': ('Israel', 'https://www.nice.com/careers/apply', 'PRIVATE', 'static'),
}
BLANK = {
    ('Israel', 'DEPT'): 1,
    ('Israel', 'HOSPITAL'): 1,
    ('Israel', 'MUNI'): 1,
    ('Israel', 'NGO'): 1,
    ('Israel', 'PRIVATE'): 49,
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
    'Israel': 11,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_mena_employers_follow_the_direct_link_rule():
    rows = _rows()
    added = [row for row in rows if row["relevance_note"].startswith(NOTE)]
    assert len(added) == len(LINKS) + sum(BLANK.values())
    found = {}
    blank = {key: 0 for key in BLANK}
    names = []
    for row in added:
        names.append((row["company_name"].casefold(), row["country"].casefold()))
        assert row["jse_code"] == ""
        assert row["official_website"] == ""
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert ":443" not in row["careers_url"]
        if row["company_name"] in LINKS:
            country, url, kind, ats = LINKS[row["company_name"]]
            assert row["country"] == country
            assert row["careers_url"] == url
            assert row["source_type"] == kind
            assert row["active"] == "true"
            assert "careers_scope=global" in row["relevance_note"]
            assert row["careers_status"] == "global_group"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
            assert detect_ats(row["careers_url"])[0] == ats
            found[row["company_name"]] = row["careers_url"]
        else:
            assert row["careers_url"] == ""
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"
            blank[(row["country"], row["source_type"])] += 1
    assert found == {name: LINKS[name][1] for name in LINKS}
    assert blank == BLANK
    assert len(names) == len(set(names))


def test_mena_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
