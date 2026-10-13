"""New employers in the countries that had the fewest careers links.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, and the page names
a post or states that there are no openings. Other new rows keep a verified
homepage and a blank careers URL.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 fewest-links"
LINKS = {
    ("Universitat d'Andorra", "Andorra"): "https://www.uda.ad/universitat/treballeu-amb-nosaltres/",
    ("Sir Lester Bird Medical Centre", "Antigua and Barbuda"): "https://www.msjmc.org/careers",
    ("University of Sarajevo", "Bosnia and Herzegovina"): "https://www.unsa.ba/konkursi",
    ("Klinički centar Univerziteta u Sarajevu", "Bosnia and Herzegovina"): "https://kcus.ba/kcus-raspisao-konkurs-za-prijem-120-novih-medicinskih-sestara-i-tehnicara/",
    ("Ministry of Health Brunei Darussalam", "Brunei"): "https://moh.gov.bn/about-us/explore-career/",
    ("Government of the Commonwealth of Dominica", "Dominica"): "https://dominica.gov.dm/vacancies",
    ("Vilnius University", "Lithuania"): "https://www.vu.lt/karjera",
    ("National University of Samoa", "Samoa"): "https://nus.edu.ws/vacancies/",
}
LINKED = {
    "Andorra": 2,
    "Antigua and Barbuda": 2,
    "Armenia": 2,
    "Bosnia and Herzegovina": 3,
    "Brunei": 2,
    "Costa Rica": 1,
    "Czechia": 1,
    "Dominica": 2,
    "Dominican Republic": 1,
    "Estonia": 1,
    "Guatemala": 1,
    "Lithuania": 2,
    "Samoa": 2,
    "Serbia": 1,
    "Slovenia": 1,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_fewest_link_batch_follows_the_direct_link_rule():
    added = [row for row in _rows() if row["relevance_note"].startswith(NOTE)]
    assert len(added) == 23
    assert len([row for row in added if row["careers_url"]]) == 8
    countries = {row["country"] for row in added}
    assert countries == set(LINKED)
    kinds = {row["source_type"] for row in added}
    assert {"DEPT", "SOE", "UNI", "HOSPITAL"} <= kinds
    for row in added:
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert ":443" not in (row["careers_url"] or "")
        if row["careers_url"]:
            assert row["active"] == "true"
            assert row["careers_status"] == "green_verified"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
        else:
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"
            assert row["official_website"].startswith("https://")


def test_verified_fewest_link_pages_stay_pinned():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    for key, url in LINKS.items():
        assert rows[key]["careers_url"] == url, key
    assert rows[("ČEZ", "Czechia")]["careers_url"] == ""
    assert rows[("Andorra Telecom", "Andorra")]["careers_url"] == ""
    assert rows[("Klinički centar Univerziteta u Sarajevu", "Bosnia and Herzegovina")]["source_type"] == "HOSPITAL"
    assert rows[("Yerevan State Medical University", "Armenia")]["source_type"] == "UNI"
    counts = {country: 0 for country in LINKED}
    for row in rows.values():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
