"""United States employers added from index lists and ATS slug probes.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, the employer's own
board names a post, and at least half of the located roles are in the United States.
Analog Devices and Equifax are the exception added later: the unfiltered Workday
board is global, and the stored URL is that board's own United States filter,
which lists the roles named in the note. Everyone else from the same lists is
a blank row.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = '2026-10-11 usa-employers'
LINKS = {
    'AbbVie': ('https://careers.smartrecruiters.com/abbvie', 'PRIVATE', 'smartrecruiters'),
    'Albemarle Corporation': ('https://albemarle.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Analog Devices': ('https://analogdevices.wd1.myworkdayjobs.com/External?locationCountry=bc33aa3152ec42d4995f4791a106ed09', 'PRIVATE', 'workday'),
    'Ameren': ('https://ameren.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Amgen': ('https://amgen.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Arista Networks': ('https://careers.smartrecruiters.com/aristanetworks', 'PRIVATE', 'smartrecruiters'),
    'Avery Dennison': ('https://careers.smartrecruiters.com/averydennison', 'PRIVATE', 'smartrecruiters'),
    'Axon Enterprise': ('https://job-boards.greenhouse.io/axon', 'PRIVATE', 'greenhouse'),
    'Brex': ('https://www.brex.com/careers', 'PRIVATE', 'static'),
    'Brown & Brown': ('https://careers.smartrecruiters.com/brownbrown', 'PRIVATE', 'smartrecruiters'),
    'Cencora': ('https://careers.smartrecruiters.com/cencora', 'PRIVATE', 'smartrecruiters'),
    'CF Industries': ('https://cfindustries.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'City of San Antonio': ('https://careers.smartrecruiters.com/cityofsanantonio', 'MUNI', 'smartrecruiters'),
    'Confluent': ('https://jobs.ashbyhq.com/confluent', 'PRIVATE', 'static'),
    'Devon Energy': ('https://devonenergy.wd5.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    "Domino's": ('https://careers.smartrecruiters.com/dominos', 'PRIVATE', 'smartrecruiters'),
    'Equifax': ('https://equifax.wd5.myworkdayjobs.com/External?locationCountry=bc33aa3152ec42d4995f4791a106ed09', 'PRIVATE', 'workday'),
    'Expeditors International': ('https://careers.smartrecruiters.com/expeditors', 'PRIVATE', 'smartrecruiters'),
    'Figma': ('https://www.figma.com/careers/', 'PRIVATE', 'static'),
    'Gen Digital': ('https://jobs.ashbyhq.com/gen-digital', 'PRIVATE', 'static'),
    'Generac': ('https://generac.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'GoDaddy': ('https://careers.godaddy/jobs/search', 'PRIVATE', 'static'),
    'Hasbro': ('https://job-boards.greenhouse.io/hasbro', 'PRIVATE', 'greenhouse'),
    'Henry Schein': ('https://careers.smartrecruiters.com/henryschein', 'PRIVATE', 'smartrecruiters'),
    'Intuitive Surgical': ('https://careers.smartrecruiters.com/intuitive', 'PRIVATE', 'smartrecruiters'),
    'Kenvue': ('https://careers.smartrecruiters.com/kenvue', 'PRIVATE', 'smartrecruiters'),
    'Labcorp': ('https://labcorp.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Leidos': ('https://leidos.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Live Nation Entertainment': ('https://careers.smartrecruiters.com/livenationentertainment', 'PRIVATE', 'smartrecruiters'),
    'Microchip Technology': ('https://careers.smartrecruiters.com/microchip', 'PRIVATE', 'smartrecruiters'),
    'Motorola Solutions': ('https://motorolasolutions.wd5.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Northwestern Medicine': ('https://careers.smartrecruiters.com/northwesternmedicine', 'HOSPITAL', 'smartrecruiters'),
    'Norwegian Cruise Line Holdings': ('https://careers.smartrecruiters.com/norwegiancruiseline', 'PRIVATE', 'smartrecruiters'),
    'OpenAI': ('https://jobs.ashbyhq.com/openai', 'PRIVATE', 'static'),
    'Penn Medicine': ('https://careers.smartrecruiters.com/pennmedicine', 'HOSPITAL', 'smartrecruiters'),
    'Plaid': ('https://jobs.ashbyhq.com/plaid', 'PRIVATE', 'static'),
    'Regeneron Pharmaceuticals': ('https://regeneron.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'ResMed': ('https://careers.smartrecruiters.com/resmed', 'PRIVATE', 'smartrecruiters'),
    'SoFi': ('https://www.sofi.com/careers/', 'PRIVATE', 'static'),
    'The Travelers Companies': ('https://travelers.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Truist Financial': ('https://truist.wd1.myworkdayjobs.com/Careers', 'PRIVATE', 'workday'),
    'Verisign': ('https://job-boards.greenhouse.io/verisign', 'PRIVATE', 'greenhouse'),
    'Wabtec': ('https://careers.smartrecruiters.com/wabtec', 'PRIVATE', 'smartrecruiters'),
    'Western Digital': ('https://careers.smartrecruiters.com/westerndigital', 'PRIVATE', 'smartrecruiters'),
    'Williams Companies': ('https://williams.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Xcel Energy': ('https://xcelenergy.wd1.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
}
BLANK_KINDS = {
    'COLLEGE': 6,
    'DEPT': 16,
    'HOSPITAL': 10,
    'MUNI': 26,
    'NGO': 10,
    'PRIVATE': 387,
    'UNI': 41,
}
LINKED_TOTAL = 374


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_usa_employers_follow_the_direct_link_rule():
    rows = _rows()
    added = [row for row in rows if row["relevance_note"].startswith(NOTE)]
    assert len(added) == len(LINKS) + sum(BLANK_KINDS.values())
    found = {}
    blank_kinds = {kind: 0 for kind in BLANK_KINDS}
    names = []
    for row in added:
        names.append(row["company_name"].casefold())
        assert row["country"] == 'United States'
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


def test_usa_employer_link_count():
    count = 0
    for row in _rows():
        if row["country"] == 'United States' and row["active"] == "true" and row["careers_url"].strip():
            count += 1
    assert count == LINKED_TOTAL
