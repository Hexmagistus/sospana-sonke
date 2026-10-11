"""Canada and Latin America employers added from market indexes and universities.

Greenhouse, Lever, Ashby and SmartRecruiters were probed. Cenovus Energy and
Waste Connections are the exception added later: the stored URL is that board's
own Canada filter, which lists the roles named in the note. Everyone else from
this list is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 americas-employers'
LINKS = {
    'Cenovus Energy Inc.': ('Canada', 'https://cenovus.wd3.myworkdayjobs.com/Careers?Location_Country=a30a87ed25634629aa6c3958aa2b91ea', 'PRIVATE', 'workday'),
    'Waste Connections Inc.': ('Canada', 'https://wasteconnections.wd1.myworkdayjobs.com/Careers?Location_Country=a30a87ed25634629aa6c3958aa2b91ea', 'PRIVATE', 'workday'),
}
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
    ('Canada', 'PRIVATE'): 57,
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
    'Canada': 12,
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


def test_americas_employers_follow_the_direct_link_rule():
    added = [row for row in _rows() if row["relevance_note"].startswith(NOTE)]
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
            assert row["careers_status"] == "green_verified"
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


def test_americas_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
