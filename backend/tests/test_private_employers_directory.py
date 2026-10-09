"""Private and listed employers added on 2026-10-09.

Careers URLs were kept only after a fetch as SospanaSonkeBot was allowed by
robots.txt, returned HTTP 200, and the page was that employer's own jobs page
or its own ATS board. Other new rows follow the blank-link convention.
"""
import csv
from pathlib import Path
from urllib.parse import urlparse

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-09"
SOUTH_AMERICA = {
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador",
    "French Guiana", "Guyana", "Paraguay", "Peru", "Suriname", "Uruguay", "Venezuela",
}
AGGREGATORS = (
    "linkedin.", "indeed.", "glassdoor.", "pnet.co.za", "erecruit.co", "hiretik.",
    "myjobmag", "brightermonday", "careers24", "jobberman.", "process-talent.com",
    "okjobs.", "vacancymail.",
)


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _batch(rows):
    return [row for row in rows if row["relevance_note"].startswith(NOTE)]


def test_new_employers_keep_the_direct_link_rule():
    rows = _rows()
    added = _batch(rows)
    assert len(added) >= 140
    linked = [row for row in added if row["careers_url"]]
    assert len(linked) >= 40
    for row in added:
        assert row["country"] not in SOUTH_AMERICA
        assert len(row["source_type"]) <= 10
        assert len(row["scraping_status"]) <= 30
        assert ":443" not in (row["careers_url"] or "")
        if row["careers_url"]:
            assert row["active"] == "true"
            assert row["careers_status"] == "green_verified"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
            host = urlparse(row["careers_url"]).netloc.lower()
            assert not any(bit in host for bit in AGGREGATORS)
        else:
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"


def test_notable_south_african_employers_and_existing_rows_stay_put():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    assert rows[("Vodacom Group", "South Africa")]["jse_code"] == "VOD"
    assert rows[("Vodacom Group", "South Africa")]["careers_url"] == "https://www.vodacom.com/careers.php"
    assert rows[("Vodacom Moçambique", "Mozambique")]["careers_url"] == "https://www.vodacom.com/search-jobs.php"
    assert rows[("Hulamin", "South Africa")]["careers_url"] == "https://hulaminjobs.mcidirecthire.com/Vacancy"
    assert rows[("Reunert", "South Africa")]["careers_url"].startswith("https://reunert.ci.hr/")
    assert rows[("Ozow", "South Africa")]["careers_url"] == "https://job-boards.greenhouse.io/ozow"
    assert rows[("Woolworths Holdings", "South Africa")]["careers_url"] == ""
    assert rows[("Woolworths Holdings", "South Africa")]["jse_code"] == "WHL"
    assert rows[("Woolworths Holdings", "South Africa")]["official_website"].startswith("https://www.woolworths.co.za")
    assert rows[("One Acre Fund", "Kenya")]["careers_url"].startswith("https://oneacrefund.org/careers/")
    assert rows[("Bell Equipment", "South Africa")]["careers_url"].startswith("https://global.bellequipment.com/")
