"""Asia-Pacific employers added from market indexes, universities, and ATS boards.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in that country.
Trend Micro is the exception added later: the stored URL is that board's own
Japan filter, which lists the roles named in the note. Alcoa stores its
Australia filter. Charter Hall, Life360, Perpetual, Bridgestone, Sumitomo
Heavy Industries, Terumo, and LG Electronics are large groups whose own board
has no country filter. Those rows are `global_group` and the note contains
`careers_scope=global`. Everyone else from the same lists is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 apac-employers'
LINKS = {
    'Alcoa': ('Australia', 'https://alcoa.wd5.myworkdayjobs.com/Careers?Location_Country=d903bb3fedad45039383f6de334ad4db', 'PRIVATE', 'workday'),
    'Arvida Group Limited': ('New Zealand', 'https://careers.smartrecruiters.com/arvida', 'PRIVATE', 'smartrecruiters'),
    'Bridgestone': ('Japan', 'https://bridgestone.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Charter Hall': ('Australia', 'https://charterhall.wd3.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Contact Energy Limited': ('New Zealand', 'https://careers.smartrecruiters.com/contactenergy', 'PRIVATE', 'smartrecruiters'),
    'Griffith University': ('Australia', 'https://careers.smartrecruiters.com/griffithuniversity', 'UNI', 'smartrecruiters'),
    'LG Electronics': ('South Korea', 'https://job-boards.greenhouse.io/lgelectronics', 'PRIVATE', 'greenhouse'),
    'Life360': ('Australia', 'https://job-boards.greenhouse.io/life360', 'PRIVATE', 'greenhouse'),
    'NextDC': ('Australia', 'https://careers.smartrecruiters.com/nextdc', 'PRIVATE', 'smartrecruiters'),
    'Perpetual': ('Australia', 'https://perpetual.wd3.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Sumitomo Heavy Industries': ('Japan', 'https://sumitomoheavyindustries.wd103.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Terumo': ('Japan', 'https://terumo.wd3.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Trend Micro': ('Japan', 'https://trendmicro.wd3.myworkdayjobs.com/External?locationCountry=8b705da2becf43cfaccc091da0988ab2', 'PRIVATE', 'workday'),
}
BLANK = {
    ('Australia', 'HOSPITAL'): 1,
    ('Australia', 'NGO'): 1,
    ('Australia', 'PRIVATE'): 107,
    ('Australia', 'UNI'): 39,
    ('India', 'DEPT'): 1,
    ('India', 'HOSPITAL'): 1,
    ('India', 'MUNI'): 1,
    ('India', 'PRIVATE'): 89,
    ('India', 'UNI'): 51,
    ('Indonesia', 'HOSPITAL'): 1,
    ('Indonesia', 'MUNI'): 1,
    ('Indonesia', 'PRIVATE'): 43,
    ('Indonesia', 'UNI'): 2,
    ('Japan', 'HOSPITAL'): 1,
    ('Japan', 'MUNI'): 1,
    ('Japan', 'NGO'): 1,
    ('Japan', 'PRIVATE'): 213,
    ('Japan', 'UNI'): 86,
    ('Malaysia', 'DEPT'): 1,
    ('Malaysia', 'MUNI'): 1,
    ('Malaysia', 'PRIVATE'): 26,
    ('Malaysia', 'UNI'): 1,
    ('New Zealand', 'HOSPITAL'): 1,
    ('New Zealand', 'MUNI'): 1,
    ('New Zealand', 'PRIVATE'): 46,
    ('New Zealand', 'UNI'): 7,
    ('Philippines', 'HOSPITAL'): 1,
    ('Philippines', 'MUNI'): 1,
    ('Philippines', 'PRIVATE'): 28,
    ('Philippines', 'UNI'): 2,
    ('Singapore', 'DEPT'): 1,
    ('Singapore', 'HOSPITAL'): 1,
    ('Singapore', 'PRIVATE'): 29,
    ('Singapore', 'SOE'): 1,
    ('Singapore', 'UNI'): 24,
    ('South Korea', 'HOSPITAL'): 1,
    ('South Korea', 'MUNI'): 1,
    ('South Korea', 'NGO'): 1,
    ('South Korea', 'PRIVATE'): 130,
    ('South Korea', 'UNI'): 44,
    ('Thailand', 'HOSPITAL'): 1,
    ('Thailand', 'MUNI'): 1,
    ('Thailand', 'PRIVATE'): 49,
    ('Thailand', 'UNI'): 2,
    ('Vietnam', 'HOSPITAL'): 1,
    ('Vietnam', 'MUNI'): 1,
    ('Vietnam', 'PRIVATE'): 3,
    ('Vietnam', 'SOE'): 2,
    ('Vietnam', 'UNI'): 1,
}
LINKED_TOTAL = {
    'India': 26,
    'Singapore': 9,
    'Australia': 36,
    'New Zealand': 11,
    'Japan': 9,
    'South Korea': 6,
    'Indonesia': 9,
    'Malaysia': 3,
    'Thailand': 2,
    'Vietnam': 1,
    'Philippines': 5,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_apac_employers_follow_the_direct_link_rule():
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
            if "careers_scope=global" in row["relevance_note"]:
                assert row["careers_status"] == "global_group"
            else:
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


def test_apac_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
