"""Careers links filled on rows that already existed.

A URL is stored only when robots.txt allows SospanaSonkeBot (or the host
publishes no robots.txt), the response is HTTP 200, and the page names a
post or states that there are no openings. Notes that already belonged to
an earlier batch keep that prefix so those counts stay intact.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
MARK = "2026-10-10 fill-blanks"
LINKS = {
    ("Adapt IT", "South Africa"): "https://adaptit.ci.hr/",
    ("Biovac", "South Africa"): "https://biovac.teamtailor.com/jobs",
    ("Dashen Bank", "Ethiopia"): "https://dashenbanksc.com/careers",
    ("IAMGOLD Essakane SA", "Burkina Faso"): "https://www.iamgoldessakane.com/offres-emplois",
    ("OPT-NC", "New Caledonia"): "https://office.opt.nc/fr/emploi-et-carriere/postuler-lopt-nc/offres-emploi",
    ("Ministry of Lands, Housing, and Country Planning", "Sierra Leone"): "https://molhcp.gov.sl/jobs/",
}
LINKED = {
    "South Africa": 813,
    "Ethiopia": 18,
    "Burkina Faso": 20,
    "New Caledonia": 5,
    "Sierra Leone": 17,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_filled_rows_keep_the_verified_pages():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    marked = [row for row in rows.values() if MARK in row["relevance_note"]]
    assert len(marked) == 6
    for key, url in LINKS.items():
        row = rows[key]
        assert row["careers_url"] == url
        assert row["active"] == "true"
        assert row["careers_status"] == "green_verified"
        assert row["scraping_status"] == "pending"
        assert MARK in row["relevance_note"]
        assert ":443" not in url
    assert rows[("Adapt IT", "South Africa")]["relevance_note"].startswith("2026-10-09 SA gap")
    assert rows[("Biovac", "South Africa")]["relevance_note"].startswith("2026-10-09")
    assert rows[("OPT-NC", "New Caledonia")]["relevance_note"].startswith("2026-10-10 territory")
    assert rows[("McCain Foods South Africa", "South Africa")]["careers_url"] == ""
    assert rows[("Petra Diamonds", "South Africa")]["careers_url"] == ""


def test_linked_counts_after_the_fill():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] in counts and row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
