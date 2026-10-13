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
    'AJ Bell': ('https://www.ajbell.co.uk/group/careers', 'PRIVATE', 'static'),
    'Alfa Financial Software': ('https://www.alfasystems.com/en-us/careers', 'PRIVATE', 'static'),
    'Antofagasta plc': ('https://www.antofagasta.co.uk/careers/', 'PRIVATE', 'static'),
    'Ashmore Group': ('https://www.ashmoregroup.com/en-gb/careers', 'PRIVATE', 'static'),
    'Associated British Foods': ('https://www.abf.co.uk/careers', 'PRIVATE', 'static'),
    'Autotrader Group': ('https://job-boards.greenhouse.io/autotrader', 'PRIVATE', 'greenhouse'),
    'Aviva': ('https://aviva.wd1.myworkdayjobs.com/External?Location_Country=29247e57dbaf46fb855b224e03170bc7', 'PRIVATE', 'workday'),
    'Babcock International': ('https://www.babcockinternational.com/careers/', 'PRIVATE', 'static'),
    'Baillie Gifford Japan Trust': ('https://www.bailliegifford.com/en/uk/individual-investors/careers/', 'PRIVATE', 'static'),
    'Balfour Beatty': ('https://www.balfourbeatty.com/careers/job-search/', 'PRIVATE', 'static'),
    'Bellway': ('https://www.bellway.co.uk/buying-with-bellway/award-winning/pride-in-the-job', 'PRIVATE', 'static'),
    'Berkeley Group Holdings': ('https://www.berkeleygroup.co.uk/about-us/careers', 'PRIVATE', 'static'),
    'BlackRock World Mining Trust': ('https://careers.blackrock.com/', 'PRIVATE', 'static'),
    'Brave Bison': ('https://careers.smartrecruiters.com/bravebison', 'PRIVATE', 'smartrecruiters'),
    'British American Tobacco': ('https://careers.bat.com/en', 'PRIVATE', 'static'),
    'British Land': ('https://www.britishland.com/careers/', 'PRIVATE', 'static'),
    'CMC Markets': ('https://www.cmcmarkets.com/group/careers', 'PRIVATE', 'static'),
    'CVS Group': ('https://www.cvsukltd.co.uk/careers/', 'PRIVATE', 'static'),
    'Centrica': ('https://www.lifeatcentrica.com/jobs/', 'PRIVATE', 'static'),
    'Ceres Power': ('https://www.ceres.tech/careers/', 'PRIVATE', 'static'),
    'Close Brothers Group': ('https://www.closebrothers.com/s/careers', 'PRIVATE', 'static'),
    'Compass Group': ('https://www.compass-group.co.uk/jobs/', 'PRIVATE', 'static'),
    'Cranswick': ('https://cranswick.plc.uk/careers/vacancies', 'PRIVATE', 'static'),
    'Croda International': ('https://www.croda.com/en-gb/careers', 'PRIVATE', 'static'),
    'Deliveroo': ('https://job-boards.greenhouse.io/deliveroo', 'PRIVATE', 'greenhouse'),
    'Dr. Martens': ('https://jobs.drmartens.com/', 'PRIVATE', 'static'),
    'Elementis': ('https://www.elementis.com/careers/', 'PRIVATE', 'static'),
    'Endeavour Mining': ('https://www.endeavourmining.com/careers/', 'PRIVATE', 'static'),
    'FRP Advisory': ('https://careers.smartrecruiters.com/frpadvisory', 'PRIVATE', 'smartrecruiters'),
    'Frasers Group': ('https://careers.smartrecruiters.com/frasersgroup', 'PRIVATE', 'smartrecruiters'),
    'Fresnillo plc': ('https://www.fresnilloplc.com/careers', 'PRIVATE', 'static'),
    'Funding Circle': ('https://jobs.ashbyhq.com/fundingcircle', 'PRIVATE', 'static'),
    'Greggs': ('https://careers.greggs.co.uk', 'PRIVATE', 'static'),
    'HSBC': ('https://www.hsbc.com/careers', 'PRIVATE', 'static'),
    'Haleon': ('https://www.haleon.com/careers', 'PRIVATE', 'static'),
    'Halfords': ('https://www.halfordscareers.com', 'PRIVATE', 'static'),
    'Helios Towers': ('https://www.heliostowers.com/careers/', 'PRIVATE', 'static'),
    'Hikma Pharmaceuticals': ('https://www.hikma.com/careers/', 'PRIVATE', 'static'),
    'Hilton Food Group': ('https://www.hiltonfoods.com/join-us/', 'PRIVATE', 'static'),
    'Howdens Joinery': ('https://careers.howdens.com/', 'PRIVATE', 'static'),
    'Imperial Brands': ('https://www.imperialbrandsplc.com/careers', 'PRIVATE', 'static'),
    'IntegraFin Holdings': ('https://www.integrafin.co.uk/careers/', 'PRIVATE', 'static'),
    'International Airlines Group': ('https://www.iairgroup.com/people-and-careers/careers/', 'PRIVATE', 'static'),
    'Intertek': ('https://www.intertek.com/careers/', 'PRIVATE', 'static'),
    'Ithaca Energy': ('https://www.ithacaenergy.com/careers', 'PRIVATE', 'static'),
    'Johnson Service Group': ('https://www.jsg.com/careers', 'PRIVATE', 'static'),
    'Lion Finance Group': ('https://lionfinancegroup.uk/careers', 'PRIVATE', 'static'),
    'Lloyds Banking Group': ('https://www.lloydsbankinggroup.com/careers', 'PRIVATE', 'static'),
    'London Stock Exchange Group': ('https://www.lseg.com/en/careers', 'PRIVATE', 'static'),
    'Man Group': ('https://job-boards.greenhouse.io/mangroup', 'PRIVATE', 'greenhouse'),
    'Marks & Spencer': ('https://jobs.marksandspencer.com/', 'PRIVATE', 'static'),
    'Metro Bank': ('https://www.metrobankonline.co.uk/about-us/careers/', 'PRIVATE', 'static'),
    'Mitie': ('https://careers.mitie.com/jobs/home/', 'PRIVATE', 'static'),
    'Mondi': ('https://www.mondigroup.com/careers/', 'PRIVATE', 'static'),
    'Moonpig': ('https://jobs.lever.co/moonpig', 'PRIVATE', 'lever'),
    'NatWest Group': ('https://www.natwestgroup.com/careers-at-natwest-group.html', 'PRIVATE', 'static'),
    'National Trust': ('https://careers.smartrecruiters.com/nationaltrust', 'NGO', 'smartrecruiters'),
    'OSB Group': ('https://www.osb.co.uk/careers/overview', 'PRIVATE', 'static'),
    'Oxford Nanopore Technologies': ('https://nanoporetech.com/about/careers', 'PRIVATE', 'static'),
    'Persimmon': ('https://www.persimmonhomes.com/corporate/careers', 'PRIVATE', 'static'),
    'Premier Foods': ('https://www.premierfoods.co.uk/careers/', 'PRIVATE', 'static'),
    'Princes Group': ('https://princescareers.com/', 'PRIVATE', 'static'),
    'Prudential plc': ('https://www.prudentialplc.com/en/careers/overview/', 'PRIVATE', 'static'),
    'Qinetiq': ('https://www.qinetiq.com/en/careers', 'PRIVATE', 'static'),
    'Reckitt': ('https://www.reckitt.com/careers/', 'PRIVATE', 'static'),
    'Renishaw': ('https://www.renishaw.com/en/careers--6417', 'PRIVATE', 'static'),
    'Rightmove': ('https://www.rightmove.co.uk/careers/', 'PRIVATE', 'static'),
    'Rotork': ('https://careers.smartrecruiters.com/rotork', 'PRIVATE', 'smartrecruiters'),
    'SSP Group': ('https://careers.foodtravelexperts.com/', 'PRIVATE', 'static'),
    'Savills': ('https://www.savills.co.uk/contact-us/careers.aspx', 'PRIVATE', 'static'),
    'Segro': ('https://www.segro.com/careers', 'PRIVATE', 'static'),
    'Shawbrook Bank': ('https://careers.shawbrook.co.uk/en/jobs', 'PRIVATE', 'static'),
    'Smith & Nephew': ('https://smithnephew.wd5.myworkdayjobs.com/External', 'PRIVATE', 'workday'),
    'Smiths Group': ('https://www.smiths.com/careers', 'PRIVATE', 'static'),
    'Softcat': ('https://www.softcat.com/careers', 'PRIVATE', 'static'),
    'Spirax Group': ('https://www.spiraxgroup.com/en/life-at-spirax/careers', 'PRIVATE', 'static'),
    'Standard Chartered': ('https://www.sc.com/en/global-careers/', 'PRIVATE', 'static'),
    'TP ICAP': ('https://careers.smartrecruiters.com/tpicap', 'PRIVATE', 'smartrecruiters'),
    'Tate & Lyle': ('https://www.tateandlyle.com/careers-0', 'PRIVATE', 'static'),
    'Taylor Wimpey': ('https://www.taylorwimpey.co.uk/jobs', 'PRIVATE', 'static'),
    'Tesco': ('https://www.tescoplc.com/careers', 'PRIVATE', 'static'),
    'Trainline': ('https://jobs.ashbyhq.com/trainline', 'PRIVATE', 'static'),
    'Travis Perkins': ('https://www.travisperkinsplc.co.uk/careers/', 'PRIVATE', 'static'),
    'UK Atomic Energy Authority': ('https://careers.smartrecruiters.com/ukatomicenergyauthority', 'SOE', 'smartrecruiters'),
    'United Utilities': ('https://www.unitedutilities.com/corporate/careers/', 'PRIVATE', 'static'),
    'Victrex': ('https://www.victrex.com/en/about-us/careers', 'PRIVATE', 'static'),
    'WPP': ('https://www.wpp.com/en/careers/search-and-apply', 'PRIVATE', 'static'),
    'Weir': ('https://www.global.weir/careers/', 'PRIVATE', 'static'),
    'Workspace Group': ('https://www.workspace.co.uk/job-vacancies', 'PRIVATE', 'static'),
}
BLANK_KINDS = {
    'DEPT': 24,
    'HOSPITAL': 271,
    'MUNI': 24,
    'NGO': 24,
    'PRIVATE': 330,
    'SOE': 14,
    'UNI': 154,
}
LINKED_TOTAL = 98


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
