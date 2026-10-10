"""National public-service recruitment pages for countries with five or fewer links.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, and the page names
a civil-service post or a concours. General labour-market boards, login
walls, and pages that only show a vacancy count were not stored.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 public-service"
LINKS = {
    ("Werkenvoor.be", "Belgium"): "https://werkenvoor.be/nl/jobs",
    ("GovJobs", "Luxembourg"): "https://govjobs.public.lu/fr.html",
    ("Posturi.gov.ro", "Romania"): "https://posturi.gov.ro/",
    ("Rijksdienst Caribisch Nederland", "Caribbean Netherlands"): (
        "https://www.rijksdienstcn.com/werken-bij-rijksdienst-caribisch-nederland/vacatures"
    ),
    ("Public Administration and Civil Service Bureau", "Macau"): (
        "https://www.safp.gov.mo/zh-hant/news/info/202610/8a674329e3e64c78aae4938506ce9093"
    ),
}
LINKED = {
    "Belgium": 6,
    "Luxembourg": 4,
    "Romania": 6,
    "Caribbean Netherlands": 1,
    "Macau": 3,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_public_service_portals_name_a_post():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    added = [row for row in rows.values() if row["relevance_note"].startswith(NOTE)]
    assert len(added) == 3
    for row in added:
        assert row["source_type"] == "DEPT"
        assert row["jse_code"] == ""
        assert len(row["company_name"]) <= 255
        assert ":443" not in row["careers_url"]
        assert row["careers_url"].startswith("https://")
        assert row["official_website"].startswith("https://")
        assert row["active"] == "true"
        assert row["careers_status"] == "green_verified"
        assert row["scraping_status"] == "pending"
        assert detect_ats(row["careers_url"])[0] == "static"
    assert {(row["company_name"], row["country"]): row["careers_url"] for row in added} == {
        key: url for key, url in LINKS.items() if key[1] in {"Belgium", "Luxembourg", "Romania"}
    }
    names = [key[0].casefold() + "|" + key[1].casefold() for key in LINKS]
    assert len(names) == len(set(names))


def test_public_service_updates_keep_their_note_prefix():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    macau = rows[("Public Administration and Civil Service Bureau", "Macau")]
    assert macau["careers_url"] == LINKS[("Public Administration and Civil Service Bureau", "Macau")]
    assert macau["relevance_note"].startswith("2026-10-10 territory")
    assert macau["active"] == "true"
    assert macau["careers_status"] == "green_verified"
    caribbean = rows[("Rijksdienst Caribisch Nederland", "Caribbean Netherlands")]
    assert caribbean["careers_url"] == LINKS[("Rijksdienst Caribisch Nederland", "Caribbean Netherlands")]
    assert caribbean["relevance_note"].startswith("2026-10-10 remaining-territories")
    assert caribbean["active"] == "true"
    assert detect_ats(macau["careers_url"])[0] == "static"
    assert detect_ats(caribbean["careers_url"])[0] == "static"


def test_public_service_link_counts():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] not in counts:
            continue
        if row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
