"""Direct boards found for blank JSE and Chile rows on 2026-10-10."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"

EXPECTED = {
    ("Arauco", "Chile"): (
        "https://jobs.arauco.com/Chile/search/?createNewAlert=false",
        "icims",
        "2026-10-10 jse-latam",
    ),
    ("Sygnia", "South Africa"): (
        "https://sygnia.simplify.hr/",
        "simplify",
        "2026-10-09 SA gap",
    ),
    ("Weaver Fintech", "South Africa"): (
        "https://weaverfintech.simplify.hr/",
        "simplify",
        "2026-10-09 SA gap",
    ),
}

LINKED = {"South Africa": 813, "Chile": 46}


def _rows():
    with CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_jse_and_chile_boards_are_the_employers_own():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    for key, (url, ats, note) in EXPECTED.items():
        row = rows[key]
        assert row["careers_url"] == url
        assert row["careers_status"] == "green_verified"
        assert row["active"] == "true"
        assert row["scraping_status"] == "pending"
        assert row["relevance_note"].startswith(note)
        assert ":443" not in url
        assert detect_ats(url)[0] == ats
    # Parque Arauco is a different employer and stays without a careers link.
    assert rows[("Parque Arauco", "Chile")]["careers_url"] == ""
    assert rows[("Parque Arauco S.A.", "Chile")]["careers_url"] == ""


def test_jse_latam_batch_raises_the_linked_counts():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
