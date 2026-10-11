"""United Kingdom employers added from index lists and ATS slug probes.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in the United Kingdom.
Aviva is the exception added later: the unfiltered Workday board is global,
and the stored URL is that board's own United Kingdom filter, which lists the
roles named in the note. Smith & Nephew is a large group whose own Workday board
has no United Kingdom filter. That row is `global_group` and the note contains
`careers_scope=global`. Everyone else from the same lists is a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 uk-employers'
LINKS = {
    'Autotrader Group': ('https://job-boards.greenhouse.io/autotrader', 'PRIVATE', 'greenhouse'),
    'Aviva': ('https://aviva.wd1.myworkdayjobs.com/External?Location_Country=29247e57dbaf46fb855b224e03170bc7', 'PRIVATE', 'workday'),
    'Brave Bison': ('https://careers.smartrecruiters.com/bravebison', 'PRIVATE', 'smartrecruiters'),
    'Deliveroo': ('https://job-boards.greenhouse.io/deliveroo', 'PRIVATE', 'greenhouse'),
    'Frasers Group': ('https://careers.smartrecruiters.com/frasersgroup', 'PRIVATE', 'smartrecruiters'),
    'FRP Advisory': ('https://careers.smartrecruiters.com/frpadvisory', 'PRIVATE', 'smartrecruiters'),
    'Funding Circle': ('https://jobs.ashbyhq.com/fundingcircle', 'PRIVATE', 'static'),
    'Man Group': ('https://job-boards.greenhouse.io/mangroup', 'PRIVATE', 'greenhouse'),
    'Moonpig': ('https://jobs.lever.co/moonpig', 'PRIVATE', 'lever'),
    'National Trust': ('https://careers.smartrecruiters.com/nationaltrust', 'NGO', 'smartrecruiters'),
    'Rotork': ('https://careers.smartrecruiters.com/rotork', 'PRIVATE', 'smartrecruiters'),
    'Shawbrook Bank': ('https://careers.shawbrook.co.uk/en/jobs', 'PRIVATE', 'static'),
    'Smith & Nephew': ('https://smithnephew.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'TP ICAP': ('https://careers.smartrecruiters.com/tpicap', 'PRIVATE', 'smartrecruiters'),
    'Trainline': ('https://jobs.ashbyhq.com/trainline', 'PRIVATE', 'static'),
    'UK Atomic Energy Authority': ('https://careers.smartrecruiters.com/ukatomicenergyauthority', 'SOE', 'smartrecruiters'),
}
BLANK_KINDS = {
    'DEPT': 24,
    'HOSPITAL': 271,
    'MUNI': 24,
    'NGO': 24,
    'PRIVATE': 403,
    'SOE': 14,
    'UNI': 154,
}
LINKED_TOTAL = 25


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_uk_employers_follow_the_direct_link_rule():
    rows = _rows()
    added = [row for row in rows if row["relevance_note"].startswith(NOTE)]
    assert len(added) == len(LINKS) + sum(BLANK_KINDS.values())
    found = {}
    blank_kinds = {kind: 0 for kind in BLANK_KINDS}
    names = []
    for row in added:
        names.append(row["company_name"].casefold())
        assert row["country"] == 'United Kingdom'
        assert row["jse_code"] == ""
        assert row["official_website"] == ""
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert ":443" not in row["careers_url"]
        if row["company_name"] in LINKS:
            url, kind, ats = LINKS[row["company_name"]]
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
            blank_kinds[row["source_type"]] += 1
    assert found == {name: LINKS[name][0] for name in LINKS}
    assert blank_kinds == BLANK_KINDS
    assert len(names) == len(set(names))


def test_uk_employer_link_count():
    count = 0
    for row in _rows():
        if row["country"] == 'United Kingdom' and row["active"] == "true" and row["careers_url"].strip():
            count += 1
    assert count == LINKED_TOTAL
