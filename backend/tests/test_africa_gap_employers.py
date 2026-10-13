"""Thin African countries, 2026-10-10.

A careers URL was stored only after a fetch as SospanaSonkeBot was allowed by
robots.txt, returned HTTP 200, and the page named a post or said there were
no openings. Procurement notices, student exams, culture pages, and boards
that need JavaScript before any title appears were left as they were.
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
MARK = "2026-10-10 africa-gap"
LINKS = {
    ("Société Béninoise d'Énergie Électrique", "Benin"): "https://recrutement.sbee.bj/",
    ("Port Autonome de Cotonou", "Benin"): "https://portdecotonou.bj/offres-demplois/",
    ("Ministère des Enseignements Maternel et Primaire", "Benin"): "https://memp.gouv.bj/opportunites/recrutements",
    ("Ministère des Affaires Sociales et de la Microfinance", "Benin"): "https://social.gouv.bj/actualites/recrutements",
    ("Mairie de Parakou", "Benin"): "https://parakou.bj/publications/recrutement-de-cinquante-50-jeunes-vulnerables",
    ("Gouvernement de la République du Bénin", "Benin"): "https://www.gouv.bj/opportunites/offres-emploi/",
    ("Electricite de Guinee EDG", "Guinea"): "https://edg.com.gn/carrieres/",
    ("Ministere de l'Economie et des Finances", "Guinea"): "https://www.mef.gov.gn/publication-mefb-avis-de-recrutement-7-postes-a-pourvoir-au-sein-de-la-mefb/",
    ("LONAGUI", "Guinea"): "https://www.lonagui.com.gn/offres-d-emploi/",
    ("Ville de Nzerekore", "Guinea"): "https://ville-nzerekore.com/emploi",
    ("SOBRAGUI", "Guinea"): "https://sobragui.com/blog/news/avis-de-recrutement-grutier/",
    ("Université Gamal Abdel Nasser de Conakry (UGANC)", "Guinea"): "https://uganc.edu.gn/category/recrutement/",
    ("Ceca-Gadis", "Gabon"): "https://cecagadis.com/offres/",
    ("Mairie de Marcory", "Côte d'Ivoire"): "https://www.marcory.ci/emploi",
    ("SAPH", "Côte d'Ivoire"): "https://www.saph.ci/carriere/offres-d-emploi",
    ("PALMCI", "Côte d'Ivoire"): "https://palmci.ci/carriere/offres-d-emploi",
    ("Ministry of Economy and Trade", "Libya"): "https://economy.gov.ly/jobs/",
    ("Ministère de la Fonction Publique, du Travail et de l'Emploi", "Niger"): "https://mfpte.gouv.ne/recrutements/",
}
BLANKS = {
    ("GITGE", "Equatorial Guinea"),
    ("Banco Central de São Tomé e Príncipe", "Sao Tome and Principe"),
    ("Commercial Bank of Eritrea", "Eritrea"),
    ("EriTel", "Eritrea"),
    ("Orotta National Referral Hospital", "Eritrea"),
}
# Active rows with a non-empty careers URL, same rule as GET /companies/stats.
LINKED = {
    "Eritrea": 2,
    "Equatorial Guinea": 2,
    "Sao Tome and Principe": 3,
    "Benin": 10,
    "Guinea": 9,
    "Gabon": 6,
    "Côte d'Ivoire": 8,
    "Libya": 7,
    "Central African Republic": 6,
    "Togo": 7,
    "Niger": 8,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_africa_gap_rows_follow_the_direct_link_rule():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    marked = [row for row in rows.values() if MARK in row["relevance_note"]]
    assert len(marked) == len(LINKS) + len(BLANKS)
    for key, url in LINKS.items():
        row = rows[key]
        assert row["careers_url"] == url
        assert row["careers_url"].startswith("https://")
        assert ":443" not in row["careers_url"]
        assert row["active"] == "true"
        assert row["careers_status"] == "green_verified"
        assert row["scraping_status"] == "pending"
        assert MARK in row["relevance_note"]
        assert not row["relevance_note"].startswith("2026-10-09")
    for key in BLANKS:
        row = rows[key]
        assert row["careers_url"] == ""
        assert row["active"] == "false"
        assert row["careers_status"] == "grey_none_verified"
        assert row["scraping_status"] == "no_url"
    assert rows[("GITGE", "Equatorial Guinea")]["official_website"] == "https://gitge.com/"
    assert rows[("Banco Central de São Tomé e Príncipe", "Sao Tome and Principe")]["official_website"] == "https://www.bcstp.st/"
    assert rows[("Orotta National Referral Hospital", "Eritrea")]["source_type"] == "HOSPITAL"
    assert rows[("Commercial Bank of Eritrea", "Eritrea")]["official_website"] == ""


def test_thin_african_countries_link_counts():
    counts = {country: 0 for country in LINKED}
    for row in _rows():
        if row["country"] not in counts:
            continue
        if row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
