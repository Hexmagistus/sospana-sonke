"""Monaco, North Macedonia, San Marino, Tajikistan, Turkmenistan and Myanmar.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host has no robots.txt), the response is HTTP 200, and the page is that
organisation's own jobs page, ATS board, or a government recruitment page of
that body. Myanmar rows leave out military-linked and sanctioned entities.
"""
import csv
from pathlib import Path
from urllib.parse import urlparse

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 six-country"
COUNTRIES = ("Monaco", "North Macedonia", "San Marino", "Tajikistan", "Turkmenistan", "Myanmar")
LISTED = {"EURONEXT", "MSE", "YSX"}
CATEGORIES = {"SOE", "DEPT", "MUNI", "NGO", "UNI", "COLLEGE", "HOSPITAL"}
BANNED = (
    "mehl", "myanmar economic corporation", "myanma oil", "mytel",
    "ministry of defence", "ministry of defense", "foreign trade bank",
    "investment and commercial bank", "five star line",
)
LINKS = {
    ("Centre Hospitalier Princesse Grace", "Monaco"): "https://www.chpg.mc/carrieres/",
    ("Direction des Ressources Humaines et de la Formation de la Fonction Publique", "Monaco"): "https://journaldemonaco.gouv.mc/fr/Journaux/2026/Journal-8813/Avis-de-recrutement-n-2026-280-d-un-Attache-au-Journal-de-Monaco",
    ("Makedonski Telekom", "North Macedonia"): "https://www.telekom.mk/kariera.nspx",
    ("Agency for Administration", "North Macedonia"): "https://www.aa.mk/interni_oglasi_2026.nspx",
    ("Red Cross of the Republic of North Macedonia", "North Macedonia"): "https://ckrm.org.mk/vrabotuvanje/",
    ("Ospedale di Stato", "San Marino"): "https://www.iss.sm/on-line/home/bandi-e-concorsi.html",
    ("Università degli Studi della Repubblica di San Marino", "San Marino"): "https://www.unirsm.sm/ateneo/bandi-e-concorsi/",
    ("Direzione Generale della Funzione Pubblica", "San Marino"): "https://gov.sm/pub1/GovSM/Bandi-Pubblici-di-Reclutamento/Concorsi-pubblici-e-selezioni.html",
    ("Tcell", "Tajikistan"): "https://www.tcell.tj/en/private-individuals/vacancies",
    ("Alif Bank", "Tajikistan"): "https://job.alif.tj/en/vacancies",
    ("FINCA Tajikistan", "Tajikistan"): "https://finca.tj/en/career/",
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _batch(rows):
    return [row for row in rows if row["relevance_note"].startswith(NOTE)]


def test_each_country_covers_the_categories_and_keeps_the_direct_link_rule():
    added = _batch(_rows())
    assert len(added) == 66
    assert len([row for row in added if row["careers_url"]]) == 11
    by_country = {}
    for row in added:
        by_country.setdefault(row["country"], []).append(row)
    assert set(by_country) == set(COUNTRIES)
    for country, rows in by_country.items():
        kinds = {row["source_type"] for row in rows}
        assert CATEGORIES <= kinds, country
        assert kinds & ({"PRIVATE"} | LISTED), country
    assert "EURONEXT" in {row["source_type"] for row in by_country["Monaco"]}
    assert "MSE" in {row["source_type"] for row in by_country["North Macedonia"]}
    assert "YSX" in {row["source_type"] for row in by_country["Myanmar"]}
    assert {row["source_type"] for row in by_country["San Marino"]} & LISTED == set()
    assert {row["source_type"] for row in by_country["Turkmenistan"]} & LISTED == set()
    for row in added:
        blob = f"{row['company_name']} {row['relevance_note']}".lower()
        assert not any(bit in blob for bit in BANNED), row["company_name"]
        if row["country"] == "Myanmar":
            assert "not added" in row["relevance_note"]
        if row["careers_url"]:
            assert row["active"] == "true"
            assert row["careers_status"] == "green_verified"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
            assert ":443" not in row["careers_url"]
            host = urlparse(row["careers_url"]).netloc.lower()
            assert "linkedin." not in host and "indeed." not in host
        else:
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"


def test_verified_six_country_careers_pages_stay_pinned():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    for key, url in LINKS.items():
        assert rows[key]["careers_url"] == url, key
    assert rows[("Monte-Carlo Société des Bains de Mer", "Monaco")]["careers_url"] == ""
    assert rows[("First Myanmar Investment Public Company Limited", "Myanmar")]["source_type"] == "YSX"
    assert rows[("Dragon Oil", "Turkmenistan")]["careers_url"] == ""
    assert rows[("Myanma Railways", "Myanmar")]["source_type"] == "SOE"
