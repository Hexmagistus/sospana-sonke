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
    "Despegar": ("Argentina", "lever"),
    "Mercado Libre": ("Argentina", "static"),
    "Globant": ("Argentina", "static"),
    "Tiendanube": ("Argentina", "static"),
    "Universidad Argentina de la Empresa (UADE)": ("Argentina", "static"),
    "Hospital Italiano de Buenos Aires": ("Argentina", "static"),
    "Cruz Roja Argentina": ("Argentina", "static"),
    "CONICET": ("Argentina", "static"),
    "iFood": ("Brazil", "greenhouse"),
    "Hotmart": ("Brazil", "static"),
    "Petrobras": ("Brazil", "static"),
    "Bradesco": ("Brazil", "static"),
    "Natura &Co": ("Brazil", "workday"),
    "Universidade de São Paulo (USP)": ("Brazil", "static"),
    "Universidade Federal do Rio de Janeiro (UFRJ)": ("Brazil", "static"),
    "Hospital Sírio-Libanês": ("Brazil", "static"),
    "Banco Central de Chile": ("Chile", "static"),
    "Pontificia Universidad Católica de Chile, Campus Villarrica": ("Chile", "static"),
    "Pontificia Universidad Católica del Perú (PUCP)": ("Peru", "static"),
    "ANTEL": ("Uruguay", "static"),
    "Universidad de la República (Udelar)": ("Uruguay", "static"),
    "Uruguay Concursa": ("Uruguay", "static"),
    "Staatsolie": ("Suriname", "static"),
    "Guyana Power and Light": ("Guyana", "static"),
    "Gobierno Autónomo Municipal de La Paz": ("Bolivia", "static"),
    "Université de Guyane": ("French Guiana", "static"),
}

# Flagship organisations whose own jobs page could not be confirmed. The link stays blank.
NO_LINK = {
    "Universidad Central de Venezuela",
    "Banco Central de Venezuela",
    "PDVSA",
    "Escuela Politécnica Nacional",
    "EP Petroecuador",
    "Banco Central de Reserva del Perú",
    "Servicio Nacional de Aprendizaje (SENA)",
    "Universidad Nacional de Asunción",
    "Universidad Mayor de San Andrés (UMSA)",
    "Universidad de Chile",
}


def test_south_america_rows_use_readable_ats_boards():
    with CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["company_name"]: row for row in rows}
    for name, (country, ats) in EXPECTED.items():
        row = by_name[name]
        assert row["country"] == country
        assert row["active"] == "true"
        assert row["careers_status"] == "direct vacancy list"
        assert row["careers_url"].startswith("https://")
        assert "trabajando." not in row["careers_url"] and "linkedin." not in row["careers_url"]
        assert len(row["scraping_status"]) <= 30
        assert len(row["source_type"]) <= 10
        assert detect_ats(row["careers_url"])[0] == ats


def test_unconfirmed_south_america_rows_keep_a_blank_careers_url():
    with CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["company_name"]: row for row in rows}
    for name in NO_LINK:
        row = by_name[name]
        assert row["careers_url"] == ""
        assert row["careers_status"] == "grey_none_verified"
        assert row["active"] == "false"
        assert row["scraping_status"] == "no_url"
