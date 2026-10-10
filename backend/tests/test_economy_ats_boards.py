"""Country-specific ATS boards added for the large economies on 2026-10-10."""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 economy-ats"

# name -> country, careers URL, ats type the scanner detects
EXPECTED = {
    "GetYourGuide": ("Germany", "https://boards.greenhouse.io/getyourguide", "greenhouse"),
    "Raisin": ("Germany", "https://boards.greenhouse.io/raisin", "greenhouse"),
    "Solaris": ("Germany", "https://boards.greenhouse.io/solarisbank", "greenhouse"),
    "BlaBlaCar": ("France", "https://jobs.lever.co/blablacar", "lever"),
    "Qonto": ("France", "https://jobs.lever.co/qonto", "lever"),
    "Algolia": ("France", "https://boards.greenhouse.io/algolia", "greenhouse"),
    "Mirakl": ("France", "https://boards.greenhouse.io/mirakl", "greenhouse"),
    "Vestiaire Collective": ("France", "https://jobs.lever.co/vestiairecollective", "lever"),
    "Swile": ("France", "https://jobs.lever.co/swile", "lever"),
    "Scaleway": ("France", "https://jobs.lever.co/scaleway", "lever"),
    "Malt": ("France", "https://jobs.lever.co/malt", "lever"),
    "Wallapop": ("Spain", "https://boards.greenhouse.io/wallapop", "greenhouse"),
    "Holded": ("Spain", "https://holded.recruitee.com/", "recruitee"),
    "Musixmatch": ("Italy", "https://jobs.lever.co/musixmatch", "lever"),
    "Sendbird": ("South Korea", "https://boards.greenhouse.io/sendbird", "greenhouse"),
    "Karrot": ("South Korea", "https://boards.greenhouse.io/daangn", "greenhouse"),
    "Mercari": ("Japan", "https://apply.workable.com/mercari/", "workable"),
    "Aldar Properties": ("United Arab Emirates", "https://jobs.lever.co/aldar", "lever"),
}

# Linked employers (active, non-empty careers URL) after this batch is
# combined with the major-economy rows already on main.
LINKED = {
    "Germany": 12,
    "France": 14,
    "Japan": 5,
    "Spain": 7,
    "Italy": 6,
    "South Korea": 5,
    "United Arab Emirates": 21,
}


def _rows():
    with CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_economy_ats_boards_are_the_employers_own_and_the_scanner_can_read_them():
    rows = _rows()
    by_name = {row["company_name"]: row for row in rows}
    marked = [row for row in rows if row["relevance_note"].startswith(NOTE)]
    assert len(marked) == len(EXPECTED)
    for name, (country, url, ats) in EXPECTED.items():
        row = by_name[name]
        assert row["country"] == country
        assert row["careers_url"] == url
        assert row["careers_status"] == "green_verified"
        assert row["active"] == "true"
        assert row["scraping_status"] == "pending"
        assert row["source_type"] == "PRIVATE"
        assert row["jse_code"] == ""
        assert row["relevance_note"].startswith(NOTE)
        assert ":443" not in url
        assert detect_ats(url)[0] == ats
    new_keys = [
        (row["company_name"].casefold(), row["country"].casefold())
        for row in rows
        if row["company_name"] in EXPECTED
    ]
    assert len(new_keys) == len(set(new_keys)) == len(EXPECTED)


def test_economy_ats_batch_raises_the_linked_counts():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] not in counts:
            continue
        if row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
