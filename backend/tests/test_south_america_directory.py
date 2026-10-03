"""South American employers added with a public ATS feed the scraper can read."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[2] / "backend" / "seed" / "company_database_import.csv"

# Companies whose link moved to their own branded careers page read as "static"; the ATS board stays in vacancy_sources.
EXPECTED = {
    "Wildlife Studios": ("Brazil", "static"),
    "Stone": ("Brazil", "greenhouse"),
    "QuintoAndar": ("Brazil", "greenhouse"),
    "VTEX": ("Brazil", "greenhouse"),
    "EBANX": ("Brazil", "static"),
    "Wellhub": ("Brazil", "greenhouse"),
    "RD Station": ("Brazil", "greenhouse"),
    "Banco Inter": ("Brazil", "greenhouse"),
    "XP Inc": ("Brazil", "greenhouse"),
    "Getnet": ("Brazil", "greenhouse"),
    "C6 Bank": ("Brazil", "greenhouse"),
    "Neon": ("Brazil", "static"),
    "RecargaPay": ("Brazil", "static"),
    "Fintual": ("Chile", "lever"),
    "Xepelin": ("Chile", "lever"),
    "Platzi": ("Colombia", "workable"),
    "Brubank": ("Argentina", "smartrecruiters"),
}


def test_south_america_rows_use_readable_ats_boards():
    with CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["company_name"]: row for row in rows}
    for name, (country, ats) in EXPECTED.items():
        row = by_name[name]
        assert row["country"] == country
        assert row["active"] == "true"
        assert row["careers_url"].startswith("https://")
        assert len(row["scraping_status"]) <= 30
        assert len(row["source_type"]) <= 10
        assert detect_ats(row["careers_url"])[0] == ats
