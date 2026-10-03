"""North American employers added with a public careers board the scraper can read."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[2] / "backend" / "seed" / "company_database_import.csv"

# Country, then the ATS detect_ats reads off the stored careers URL.
# Companies whose link moved to their own branded careers page read as "static"; the ATS board stays in vacancy_sources.
# Companies whose link moved to their own branded careers page read as "static"; the ATS board stays in vacancy_sources.
EXPECTED = {
    "NVIDIA": ("United States", "static"),
    "Boeing": ("United States", "static"),
    "Disney": ("United States", "static"),
    "Stripe": ("United States", "static"),
    "Airbnb": ("United States", "static"),
    "Block": ("United States", "static"),
    "Robinhood": ("United States", "static"),
    "Palantir": ("United States", "lever"),
    "Anthropic": ("United States", "static"),
    "Scale AI": ("United States", "static"),
    "Reddit": ("United States", "static"),
    "GitLab": ("United States", "static"),
    "Affirm": ("United States", "static"),
    "Twilio": ("United States", "static"),
    "Discord": ("United States", "static"),
    "Gusto": ("United States", "static"),
    "Coursera": ("United States", "static"),
    "Khan Academy": ("United States", "static"),
    "Airtable": ("United States", "greenhouse"),
    "Royal Bank of Canada": ("Canada", "static"),
    "TD Bank": ("Canada", "static"),
    "Manulife": ("Canada", "workday"),
    "Nuvei": ("Canada", "static"),
    "Hootsuite": ("Canada", "static"),
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
