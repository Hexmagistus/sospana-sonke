"""Asian employers added with a public careers URL the scraper can read."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[2] / "backend" / "seed" / "company_database_import.csv"

# (company, country, ats). Uniqlo is one employer name in several countries;
# the key is the pair, matching the importer.
EXPECTED = [
    ("Razorpay", "India", "greenhouse"),
    ("Groww", "India", "greenhouse"),
    ("InMobi", "India", "greenhouse"),
    ("Meesho", "India", "lever"),
    ("CRED", "India", "lever"),
    ("Sigmoid", "India", "greenhouse"),
    ("PayPay", "Japan", "greenhouse"),
    ("SmartNews", "Japan", "workable"),
    ("Krafton", "South Korea", "greenhouse"),
    ("Grab", "Singapore", "smartrecruiters"),
    ("DBS Bank", "Singapore", "workday"),
    ("Ninja Van", "Singapore", "lever"),
    ("Nium", "Singapore", "lever"),
    ("MoneySmart", "Singapore", "greenhouse"),
    ("Singapore Public Service", "Singapore", "workday"),
    ("Uniqlo", "Singapore", "workday"),
    ("Uniqlo", "Malaysia", "workday"),
    ("Xendit", "Indonesia", "greenhouse"),
    ("Uniqlo", "Indonesia", "workday"),
    ("Mynt (GCash)", "Philippines", "workday"),
    ("Uniqlo", "Philippines", "workday"),
    ("Agoda", "Thailand", "greenhouse"),
    ("Uniqlo", "Thailand", "workday"),
    ("Uniqlo", "Vietnam", "workday"),
    ("Tamara", "Saudi Arabia", "greenhouse"),
    ("Foodics", "Saudi Arabia", "workable"),
    ("Similarweb", "Israel", "greenhouse"),
    ("Payoneer", "Israel", "static"),
    ("Trendyol", "Turkey", "lever"),
    ("Dream Games", "Turkey", "lever"),
    ("Midas", "Turkey", "lever"),
    ("Lalamove", "Hong Kong", "lever"),
    ("Uniqlo", "Hong Kong", "workday"),
    ("Appier", "Taiwan", "greenhouse"),
    ("Dcard", "Taiwan", "greenhouse"),
    ("Etihad Airways", "United Arab Emirates", "smartrecruiters"),
    ("DP World", "United Arab Emirates", "oracle"),
]


def test_asia_rows_use_readable_career_boards():
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
