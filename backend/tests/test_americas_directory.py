"""Americas employers added with a public careers board the scraper can read."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[2] / "backend" / "seed" / "company_database_import.csv"

# (company, country, ats). Three UWI campuses share a name stem and stay separate rows.
EXPECTED = [
    ("University of Pennsylvania", "United States", "workday"),
    ("Cleveland Clinic", "United States", "workday"),
    ("Stanford Health Care", "United States", "workday"),
    ("Mass General Brigham", "United States", "workday"),
    ("Mayo Clinic", "United States", "oracle"),
    ("American Red Cross", "United States", "workday"),
    ("New York City School Construction Authority", "United States", "workday"),
    ("City of New York", "United States", "static"),
    ("University of British Columbia", "Canada", "workday"),
    ("McGill University", "Canada", "workday"),
    ("University of Waterloo", "Canada", "workday"),
    ("University of Toronto", "Canada", "static"),
    ("Public Health Ontario", "Canada", "workday"),
    ("Spin (FEMSA)", "Mexico", "greenhouse"),
    ("Rappi", "Colombia", "workday"),
    ("dLocal", "Uruguay", "lever"),
    ("Devsu", "Ecuador", "workable"),
    ("Vana", "Guatemala", "lever"),
    ("University of the West Indies, Mona", "Jamaica", "static"),
    ("University of the West Indies, St. Augustine", "Trinidad and Tobago", "static"),
    ("University of the West Indies, Cave Hill", "Barbados", "static"),
]


def test_americas_rows_use_readable_career_boards():
    with CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_key = {(row["company_name"], row["country"]): row for row in rows}
    for name, country, ats in EXPECTED:
        row = by_key[(name, country)]
        assert row["active"] == "true"
        assert row["careers_status"] == "direct vacancy list"
        assert row["careers_url"].startswith("https://")
        assert len(row["scraping_status"]) <= 30
        assert len(row["source_type"]) <= 10
        assert detect_ats(row["careers_url"])[0] == ats
