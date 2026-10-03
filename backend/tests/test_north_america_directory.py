"""North American employers added with a public careers board the scraper can read."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[2] / "backend" / "seed" / "company_database_import.csv"

# Country, then the ATS detect_ats reads off the stored careers URL.
EXPECTED = {
    "NVIDIA": ("United States", "workday"),
    "Boeing": ("United States", "workday"),
    "Disney": ("United States", "workday"),
    "Stripe": ("United States", "greenhouse"),
    "Airbnb": ("United States", "greenhouse"),
    "Block": ("United States", "greenhouse"),
    "Robinhood": ("United States", "greenhouse"),
    "Palantir": ("United States", "lever"),
    "Anthropic": ("United States", "greenhouse"),
    "Scale AI": ("United States", "greenhouse"),
    "Reddit": ("United States", "greenhouse"),
    "GitLab": ("United States", "greenhouse"),
    "Affirm": ("United States", "greenhouse"),
    "Twilio": ("United States", "greenhouse"),
    "Discord": ("United States", "greenhouse"),
    "Gusto": ("United States", "greenhouse"),
    "Coursera": ("United States", "greenhouse"),
    "Khan Academy": ("United States", "greenhouse"),
    "Airtable": ("United States", "greenhouse"),
    "Royal Bank of Canada": ("Canada", "workday"),
    "TD Bank": ("Canada", "workday"),
    "Manulife": ("Canada", "workday"),
    "Nuvei": ("Canada", "workable"),
    "Hootsuite": ("Canada", "greenhouse"),
    "Kavak": ("Mexico", "workday"),
    "Clara": ("Mexico", "greenhouse"),
    "Digicel": ("Jamaica", "static"),
    "Copa Airlines": ("Panama", "oracle"),
}


def test_north_america_rows_use_readable_career_boards():
    with CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["company_name"]: row for row in rows}
    for name, (country, ats) in EXPECTED.items():
        row = by_name[name]
        assert row["country"] == country
        assert row["active"] == "true"
        assert row["careers_status"] == "direct vacancy list"
        assert row["careers_url"].startswith("https://")
        assert len(row["scraping_status"]) <= 30
        assert len(row["source_type"]) <= 10
        assert detect_ats(row["careers_url"])[0] == ats
