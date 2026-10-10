"""European ATS boards and three university staff pages.

A careers URL is stored only when the employer is headquartered in a European
country that had five or fewer links, robots.txt allows SospanaSonkeBot (or
the host publishes no robots.txt), the response is HTTP 200, the page names
a post, and at least half of the located roles are in that country.
"""
import csv
from pathlib import Path

from app.scraper.base import detect_ats

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 europe-boards"
LINKS = {
    ("Schibsted", "Norway"): "https://schibsted.teamtailor.com/jobs",
    ("Itera", "Norway"): "https://careers.itera.com/jobs",
    ("Veidekke", "Norway"): "https://veidekke.teamtailor.com/jobs",
    ("University of Oslo", "Norway"): "https://www.uio.no/english/about/vacancies/last-published.html",
    ("Lunar", "Denmark"): "https://jobs.lunar.app/jobs",
    ("Matas", "Denmark"): "https://matas.teamtailor.com/jobs",
    ("Power Danmark", "Denmark"): "https://power.teamtailor.com/jobs",
    ("Templafy", "Denmark"): "https://templafy.teamtailor.com/jobs",
    ("Siili Solutions", "Finland"): "https://siili.teamtailor.com/jobs",
    ("Aalto University", "Finland"): "https://www.aalto.fi/en/open-positions",
    ("University of Iceland", "Iceland"): "https://english.hi.is/about-ui/working-ui/vacancies",
    ("RebelDot", "Romania"): "https://careers.rebeldot.com/jobs",
    ("Technord", "Belgium"): "https://jobs.technord.com/",
    ("Xylos", "Belgium"): "https://xylos.recruitee.com/",
}
KINDS = {
    "University of Oslo": "UNI",
    "Aalto University": "UNI",
    "University of Iceland": "UNI",
}
LINKED = {
    "Belgium": 6,
    "Denmark": 6,
    "Finland": 4,
    "Iceland": 5,
    "Norway": 7,
    "Romania": 6,
}
SITES = {
    "Schibsted": "https://schibsted.com/",
    "Itera": "https://www.itera.com/",
    "Veidekke": "https://www.veidekke.com/",
    "University of Oslo": "https://www.uio.no/",
    "Lunar": "https://www.lunar.app/",
    "Matas": "https://www.matas.dk/",
    "Power Danmark": "https://www.power.dk/",
    "Templafy": "https://www.templafy.com/",
    "Siili Solutions": "https://www.siili.com/",
    "Aalto University": "https://www.aalto.fi/",
    "University of Iceland": "https://english.hi.is/",
    "RebelDot": "https://www.rebeldot.com/",
    "Technord": "https://www.technord.com/",
    "Xylos": "",
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_europe_boards_name_a_post():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    added = [row for row in rows.values() if row["relevance_note"].startswith(NOTE)]
    assert len(added) == len(LINKS)
    found = {}
    for row in added:
        key = (row["company_name"], row["country"])
        assert key in LINKS
        found[key] = row["careers_url"]
        assert row["careers_url"] == LINKS[key]
        assert row["source_type"] == KINDS.get(row["company_name"], "PRIVATE")
        assert row["jse_code"] == ""
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert ":443" not in row["careers_url"]
        assert row["careers_url"].startswith("https://")
        assert row["official_website"] == SITES[row["company_name"]]
        assert row["active"] == "true"
        assert row["careers_status"] == "green_verified"
        assert row["scraping_status"] == "pending"
        kind = "recruitee" if "recruitee.com" in row["careers_url"] else "static"
        assert detect_ats(row["careers_url"])[0] == kind
    assert found == LINKS
    names = [name.casefold() + "|" + country.casefold() for name, country in LINKS]
    assert len(names) == len(set(names))


def test_europe_board_link_counts():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] not in counts:
            continue
        if row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
