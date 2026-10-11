"""European employers added from national indexes, universities, and ATS boards.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in that country.
Everyone else from the same lists is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 europe-employers'
LINKS = {
    'Boskalis': ('Netherlands', 'https://careers.smartrecruiters.com/boskalis', 'PRIVATE', 'smartrecruiters'),
    'Gerresheimer': ('Germany', 'https://careers.smartrecruiters.com/gerresheimer', 'PRIVATE', 'smartrecruiters'),
    'Saint-Gobain': ('France', 'https://careers.smartrecruiters.com/saintgobain', 'PRIVATE', 'smartrecruiters'),
    'Scout24': ('Germany', 'https://www.scout24.com/en/career/jobs', 'PRIVATE', 'static'),
    'Swissquote': ('Switzerland', 'https://careers.smartrecruiters.com/swissquote', 'PRIVATE', 'smartrecruiters'),
    'Vattenfall': ('Sweden', 'https://careers.vattenfall.com/', 'SOE', 'static'),
}
BLANK = {
    ('Denmark', 'HOSPITAL'): 1,
    ('Denmark', 'MUNI'): 1,
    ('Denmark', 'NGO'): 1,
    ('Denmark', 'PRIVATE'): 21,
    ('Denmark', 'SOE'): 1,
    ('Denmark', 'UNI'): 6,
    ('Finland', 'HOSPITAL'): 1,
    ('Finland', 'NGO'): 1,
    ('Finland', 'PRIVATE'): 23,
    ('Finland', 'UNI'): 12,
    ('France', 'DEPT'): 2,
    ('France', 'HOSPITAL'): 2,
    ('France', 'MUNI'): 3,
    ('France', 'NGO'): 2,
    ('France', 'PRIVATE'): 33,
    ('France', 'SOE'): 4,
    ('France', 'UNI'): 68,
    ('Germany', 'DEPT'): 3,
    ('Germany', 'HOSPITAL'): 3,
    ('Germany', 'MUNI'): 4,
    ('Germany', 'NGO'): 2,
    ('Germany', 'PRIVATE'): 139,
    ('Germany', 'SOE'): 2,
    ('Germany', 'UNI'): 79,
    ('Iceland', 'HOSPITAL'): 1,
    ('Iceland', 'MUNI'): 1,
    ('Iceland', 'PRIVATE'): 3,
    ('Iceland', 'UNI'): 6,
    ('Ireland', 'HOSPITAL'): 1,
    ('Ireland', 'PRIVATE'): 1,
    ('Ireland', 'SOE'): 2,
    ('Ireland', 'UNI'): 7,
    ('Italy', 'HOSPITAL'): 1,
    ('Italy', 'MUNI'): 2,
    ('Italy', 'NGO'): 1,
    ('Italy', 'PRIVATE'): 34,
    ('Italy', 'SOE'): 1,
    ('Italy', 'UNI'): 88,
    ('Netherlands', 'DEPT'): 1,
    ('Netherlands', 'HOSPITAL'): 7,
    ('Netherlands', 'MUNI'): 2,
    ('Netherlands', 'NGO'): 1,
    ('Netherlands', 'PRIVATE'): 37,
    ('Netherlands', 'SOE'): 1,
    ('Netherlands', 'UNI'): 29,
    ('Norway', 'HOSPITAL'): 1,
    ('Norway', 'MUNI'): 1,
    ('Norway', 'NGO'): 1,
    ('Norway', 'PRIVATE'): 23,
    ('Norway', 'UNI'): 31,
    ('Poland', 'HOSPITAL'): 1,
    ('Poland', 'MUNI'): 2,
    ('Poland', 'NGO'): 1,
    ('Poland', 'PRIVATE'): 27,
    ('Poland', 'SOE'): 1,
    ('Poland', 'UNI'): 20,
    ('Spain', 'HOSPITAL'): 2,
    ('Spain', 'MUNI'): 2,
    ('Spain', 'NGO'): 1,
    ('Spain', 'PRIVATE'): 28,
    ('Spain', 'SOE'): 1,
    ('Spain', 'UNI'): 93,
    ('Sweden', 'HOSPITAL'): 1,
    ('Sweden', 'MUNI'): 1,
    ('Sweden', 'NGO'): 1,
    ('Sweden', 'PRIVATE'): 25,
    ('Sweden', 'UNI'): 10,
    ('Switzerland', 'HOSPITAL'): 2,
    ('Switzerland', 'MUNI'): 2,
    ('Switzerland', 'NGO'): 1,
    ('Switzerland', 'PRIVATE'): 43,
    ('Switzerland', 'SOE'): 1,
    ('Switzerland', 'UNI'): 11,
}
LINKED_TOTAL = {
    'Germany': 14,
    'France': 15,
    'Netherlands': 9,
    'Ireland': 6,
    'Norway': 7,
    'Sweden': 7,
    'Denmark': 6,
    'Finland': 4,
    'Iceland': 5,
    'Spain': 7,
    'Italy': 6,
    'Switzerland': 6,
    'Poland': 5,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_europe_region_employers_follow_the_direct_link_rule():
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


def test_europe_region_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
