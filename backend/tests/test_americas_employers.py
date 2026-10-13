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
    'Bancolombia': ('Colombia', 'https://www.grupobancolombia.com/en/careers', 'PRIVATE', 'static'),
    'Brookfield Corporation': ('Canada', 'https://www.brookfield.com/careers/life-at-brookfield', 'PRIVATE', 'static'),
    'CAE Inc.': ('Canada', 'https://www.cae.com/careers', 'PRIVATE', 'static'),
    'CGI Inc.': ('Canada', 'https://www.cgi.com/en/careers', 'PRIVATE', 'static'),
    'Cameco Corporation': ('Canada', 'https://www.cameco.com/careers', 'PRIVATE', 'static'),
    'Canadian National Railway Company': ('Canada', 'https://www.cn.ca/en/careers/', 'PRIVATE', 'static'),
    'Canadian Natural Resources Limited': ('Canada', 'https://www.cnrl.com/careers/careers-with-canadian-natural/', 'PRIVATE', 'static'),
    'Canadian Pacific Kansas City Limited': ('Canada', 'https://www.cpkcr.com/en/careers.html', 'PRIVATE', 'static'),
    'Celestica Inc.': ('Canada', 'https://www.celestica.com/careers/working-at-celestica', 'PRIVATE', 'static'),
    'Cemex': ('Mexico', 'https://www.cemexusa.com/careers', 'PRIVATE', 'static'),
    'Cenovus Energy Inc.': ('Canada', 'https://cenovus.wd3.myworkdayjobs.com/Careers?Location_Country=a30a87ed25634629aa6c3958aa2b91ea', 'PRIVATE', 'workday'),
    'Davivienda': ('Colombia', 'https://www.davivienda.com/careers', 'PRIVATE', 'static'),
    'Dollarama Inc.': ('Canada', 'https://www.dollarama.com/en-ca/faq/careers/store/', 'PRIVATE', 'static'),
    'Emera Incorporated': ('Canada', 'https://careers.emera.com/careers-home', 'PRIVATE', 'static'),
    'Enbridge Inc.': ('Canada', 'https://www.enbridge.com/work-with-enbridge/careers', 'PRIVATE', 'static'),
    'First Quantum Minerals Ltd.': ('Canada', 'https://www.first-quantum.com/careers/', 'PRIVATE', 'static'),
    'FirstService Corporation': ('Canada', 'https://www.firstservice.com/careers/', 'PRIVATE', 'static'),
    'Fortis Inc.': ('Canada', 'https://www.fortisinc.com/careers', 'PRIVATE', 'static'),
    'Grupo Aeroportuario Centro Norte': ('Mexico', 'https://www.oma.aero/es/grupo-oma/oportunidades-de-empleo/', 'PRIVATE', 'static'),
    'Hydro One Limited': ('Canada', 'https://www.hydroone.com/careers', 'PRIVATE', 'static'),
    'Imperial Oil Limited': ('Canada', 'https://www.imperialoil.ca/careers/careers', 'PRIVATE', 'static'),
    'Loblaw Companies Limited': ('Canada', 'https://careers.loblaw.ca', 'PRIVATE', 'static'),
    'Magna International Inc.': ('Canada', 'https://www.magna.com/careers', 'PRIVATE', 'static'),
    'Open Text Corporation': ('Canada', 'https://careers.opentext.com/us/en', 'PRIVATE', 'static'),
    'Rogers Communications Inc.': ('Canada', 'https://jobs.rogers.com/', 'PRIVATE', 'static'),
    'Saputo Inc.': ('Canada', 'https://saputo.wd5.myworkdayjobs.com/en-US/Saputo_External_Careers?locationCountry=a30a87ed25634629aa6c3958aa2b91ea', 'PRIVATE', 'workday'),
    'Shopify Inc.': ('Canada', 'https://www.shopify.com/careers', 'PRIVATE', 'static'),
    'TC Energy Corporation': ('Canada', 'https://www.tcenergy.com/about/careers/', 'PRIVATE', 'static'),
    'Teck Resources Limited': ('Canada', 'https://www.teck.com/careers/', 'PRIVATE', 'static'),
    'Thomson Reuters Corporation': ('Canada', 'https://www.thomsonreuters.com/en/careers', 'PRIVATE', 'static'),
    'Toronto-Dominion Bank': ('Canada', 'https://careers.td.com/', 'PRIVATE', 'static'),
    'Tourmaline Oil Corp.': ('Canada', 'https://www.tourmalineoil.com/careers', 'PRIVATE', 'static'),
    'Volaris': ('Mexico', 'https://www.volaris.com/careers', 'PRIVATE', 'static'),
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
    ('Canada', 'PRIVATE'): 30,
    ('Canada', 'SOE'): 1,
    ('Canada', 'UNI'): 92,
    ('Colombia', 'PRIVATE'): 13,
    ('Ecuador', 'PRIVATE'): 9,
    ('Ecuador', 'UNI'): 1,
    ('Mexico', 'HOSPITAL'): 1,
    ('Mexico', 'MUNI'): 1,
    ('Mexico', 'PRIVATE'): 29,
    ('Mexico', 'UNI'): 2,
    ('Uruguay', 'PRIVATE'): 4,
    ('Uruguay', 'UNI'): 1,
}
LINKED_TOTAL = {
    'Canada': 39,
    'Mexico': 6,
    'Brazil': 435,
    'Argentina': 82,
    'Colombia': 23,
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


def test_americas_employer_link_counts():
    counts = {country: 0 for country in LINKED_TOTAL}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED_TOTAL
