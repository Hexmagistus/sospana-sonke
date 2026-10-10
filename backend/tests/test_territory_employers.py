"""Puerto Rico, Réunion, Macau, Greenland and New Caledonia, added 2026-10-10.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host has no robots.txt), the response is HTTP 200, and the page is that
organisation's own jobs, recrutement, vacancies or concours page, or its own
ATS board. Every other new row uses the blank-link convention.
"""
import csv
from pathlib import Path
from urllib.parse import urlparse

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 territory"
TERRITORIES = ("Puerto Rico", "Réunion", "Macau", "Greenland", "New Caledonia")
LISTED = {"NASDAQ", "NYSE", "HKEX", "EURONEXT"}
CATEGORIES = {"SOE", "DEPT", "MUNI", "NGO", "UNI", "COLLEGE", "HOSPITAL"}
AGGREGATORS = (
    "linkedin.", "indeed.", "glassdoor.", "pnet.co.za", "erecruit.co",
    "careers24", "jobscall", "jobwonders", "hireme.gl", "sjob.gl", "arbejd.com",
    "github.io",
)
LINKS = {
    ("Popular, Inc.", "Puerto Rico"): "https://jobs.popular.com/search/",
    ("Departamento del Trabajo y Recursos Humanos", "Puerto Rico"): "https://www.trabajo.pr.gov/convocatorias.asp",
    ("Oficina de Administración y Transformación de los Recursos Humanos", "Puerto Rico"): "https://empleos.pr.gov/",
    ("Universidad de Puerto Rico", "Puerto Rico"): "https://www.empleos.pr.gov/convocatorias/upr",
    ("Puerto Rico Industrial Development Company", "Puerto Rico"): "https://www.pridco.pr.gov/announcement/convocatoria-interna-g001-2026---oficial-de-asuntos-gerenciales",
    ("Université de La Réunion", "Réunion"): "https://www.univ-reunion.fr/decouvrir-luniversite/nous-rejoindre/recrutements/",
    ("Centre Hospitalier Universitaire de La Réunion", "Réunion"): "https://chu-reunion-sud.mstaff.co/offers",
    ("Département de La Réunion", "Réunion"): "https://recrutement.departement974.fr/search",
    ("Companhia de Electricidade de Macau", "Macau"): "https://www.cem-macau.com/zh/about-cem/working-at-cem/job-opportunities/",
    ("Macau University of Science and Technology", "Macau"): "https://hro.must.edu.mo/page/careers.html?locale=zh_MO",
    ("Université de la Nouvelle-Calédonie", "New Caledonia"): "https://www.unc.nc/utile/recrutement/recrutement-emplois-stages/",
    ("Société Le Nickel", "New Caledonia"): "https://sln.eramet.com/sln/nos-talents/offres-demploi/",
    ("Centre Hospitalier Territorial Gaston-Bourret", "New Caledonia"): "https://recrutement.cht.nc/",
    ("Direction des ressources humaines et de la fonction publique de Nouvelle-Calédonie", "New Caledonia"): "https://drhfpnc.gouv.nc/avis-vacances-postes-AVP",
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _batch(rows):
    return [row for row in rows if row["relevance_note"].startswith(NOTE)]


def test_each_territory_covers_every_category_and_keeps_the_direct_link_rule():
    added = _batch(_rows())
    assert len(added) == 73
    linked = [row for row in added if row["careers_url"]]
    assert len(linked) == 14
    by_country = {}
    for row in added:
        by_country.setdefault(row["country"], []).append(row)
    assert set(by_country) == set(TERRITORIES)
    for country, rows in by_country.items():
        kinds = {row["source_type"] for row in rows}
        assert CATEGORIES <= kinds, country
        assert kinds & ({"PRIVATE"} | LISTED), country
        assert any(row["careers_url"] for row in rows) or country == "Greenland"
    assert {row["source_type"] for row in by_country["New Caledonia"]} & LISTED == set()
    for row in added:
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert len(row["scraping_status"]) <= 30
        assert ":443" not in (row["careers_url"] or "")
        if row["careers_url"]:
            assert row["active"] == "true"
            assert row["careers_status"] == "green_verified"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
            host = urlparse(row["careers_url"]).netloc.lower()
            assert not any(bit in host for bit in AGGREGATORS)
        else:
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"
            assert row["careers_url"] == ""


def test_verified_territory_careers_pages_stay_pinned():
    rows = {(row["company_name"], row["country"]): row for row in _rows()}
    for key, url in LINKS.items():
        assert rows[key]["careers_url"] == url, key
        assert rows[key]["relevance_note"].startswith(NOTE)
    assert rows[("GrønlandsBANKEN", "Greenland")]["careers_url"] == ""
    assert rows[("GrønlandsBANKEN", "Greenland")]["source_type"] == "NASDAQ"
    assert rows[("SJM Holdings", "Macau")]["source_type"] == "HKEX"
    assert rows[("CBo Territoria", "Réunion")]["source_type"] == "EURONEXT"
    assert rows[("Centre Hospitalier Universitaire de La Réunion", "Réunion")]["source_type"] == "HOSPITAL"
    assert rows[("Société Le Nickel", "New Caledonia")]["source_type"] == "PRIVATE"
