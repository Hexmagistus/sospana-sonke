"""Major economies that had five or fewer careers links, 2026-10-10.

A careers URL was stored only after a fetch as SospanaSonkeBot was allowed by
robots.txt, returned HTTP 200, and the page named a post. Culture pages,
cookie banners, investor "analyst coverage", and boards whose HTML had no
job title were not stored.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
MARK = "2026-10-10 major-economy"
LINKS = {
    ("BMW Group", "Germany"): "https://www.bmwgroup.jobs/en.html",
    ("Volkswagen Group", "Germany"): "https://www.volkswagen-karriere.de/de.html",
    ("Deutsche Bahn", "Germany"): "https://db.jobs/de-de",
    ("Deutsche Bank", "Germany"): "https://careers.db.com/professionals/search-roles/",
    ("Société Générale", "France"): "https://careers.societegenerale.com/",
    ("Telefónica", "Spain"): "https://jobs.telefonica.com/search/",
    ("Saudi Aramco", "Saudi Arabia"): "https://www.aramco.com/en/careers",
    ("Panasonic Group", "Japan"): "https://recruit.jpn.panasonic.com/newgrads/job_description/",
}
LINKED = {
    "Germany": 9,
    "France": 6,
    "Japan": 4,
    "Mexico": 3,
    "Spain": 5,
    "Italy": 5,
    "China": 3,
    "South Korea": 3,
    "Turkey": 4,
    "Saudi Arabia": 4,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_major_economy_rows_name_a_post():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    marked = [row for row in rows.values() if MARK in row["relevance_note"]]
    assert len(marked) == len(LINKS)
    for key, url in LINKS.items():
        row = rows[key]
        assert row["careers_url"] == url
        assert row["careers_url"].startswith("https://")
        assert ":443" not in row["careers_url"]
        assert row["active"] == "true"
        assert row["careers_status"] == "green_verified"
        assert row["scraping_status"] == "pending"
        assert row["official_website"].startswith("https://")
        assert not row["relevance_note"].startswith("2026-10-09")
    assert rows[("Deutsche Bahn", "Germany")]["source_type"] == "SOE"
    assert rows[("Saudi Aramco", "Saudi Arabia")]["source_type"] == "SOE"


def test_major_economy_link_counts():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] not in counts:
            continue
        if row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
