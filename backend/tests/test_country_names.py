"""Country spellings collapse to the homepage name, and non-countries are not counted."""
import csv
from pathlib import Path

from app.db import session as db_session
from app.models.company import Company
from app.services.country_names import COUNTRY_ALIASES, NON_COUNTRY_BUCKETS, canonical_country
from app.services.csv_import import import_companies_from_csv

_SEED = Path(__file__).resolve().parents[1] / "seed"


def test_aliases_map_to_homepage_spellings_and_leave_dr_congo():
    assert canonical_country("São Tomé and Príncipe") == "Sao Tome and Principe"
    assert canonical_country("Sao Tome and Principe") == "Sao Tome and Principe"
    assert canonical_country("Cote dIvoire") == "Côte d'Ivoire"
    assert canonical_country("Ivory Coast") == "Côte d'Ivoire"
    assert canonical_country("Côte d'Ivoire") == "Côte d'Ivoire"
    assert canonical_country("Cape Verde") == "Cabo Verde"
    assert canonical_country("Republic of Congo") == "Congo"
    assert canonical_country("Republic of the Congo") == "Congo"
    assert canonical_country("DR Congo") == "DR Congo"
    assert canonical_country("Congo") == "Congo"
    assert "DR Congo" not in COUNTRY_ALIASES
    assert NON_COUNTRY_BUCKETS == frozenset({"International", "Africa"})


def test_directory_stats_collapse_spellings_and_skip_non_countries(client, db):
    rows = [
        ("STP Accent", "São Tomé and Príncipe"),
        ("STP Plain", "Sao Tome and Principe"),
        ("CI Home", "Côte d'Ivoire"),
        ("CI Ivory", "Ivory Coast"),
        ("CI Ascii", "Cote dIvoire"),
        ("CV Home", "Cabo Verde"),
        ("CV Alias", "Cape Verde"),
        ("CG Home", "Congo"),
        ("CG Alias", "Republic of Congo"),
        ("DRC", "DR Congo"),
        ("Intl", "International"),
        ("Continental", "Africa"),
    ]
    for name, country in rows:
        db.add(Company(company_name=name, country=country, active=True))
    db.commit()

    body = client.get("/api/v1/companies/stats").json()
    assert body["by_country"]["Sao Tome and Principe"] == 2
    assert "São Tomé and Príncipe" not in body["by_country"]
    assert body["by_country"]["Côte d'Ivoire"] == 3
    assert "Ivory Coast" not in body["by_country"]
    assert "Cote dIvoire" not in body["by_country"]
    assert body["by_country"]["Cabo Verde"] == 2
    assert "Cape Verde" not in body["by_country"]
    assert body["by_country"]["Congo"] == 2
    assert "Republic of Congo" not in body["by_country"]
    assert body["by_country"]["DR Congo"] == 1
    assert body["by_country"]["International"] == 1
    assert body["by_country"]["Africa"] == 1
    real = [name for name in body["by_country"] if name not in NON_COUNTRY_BUCKETS]
    assert body["countries"] == len(real)
    assert body["employers"] >= len(rows)


def test_startup_normalise_is_idempotent(db_engine):
    from sqlalchemy.orm import sessionmaker

    db_session.engine = db_engine
    Session = sessionmaker(bind=db_engine)
    db = Session()
    db.add(Company(company_name="STP Accent", country="São Tomé and Príncipe"))
    db.add(Company(company_name="CI Ivory", country="Ivory Coast"))
    db.add(Company(company_name="CI Ascii", country="Cote dIvoire"))
    db.add(Company(company_name="CV Alias", country="Cape Verde"))
    db.add(Company(company_name="CG Alias", country="Republic of Congo"))
    db.add(Company(company_name="DRC", country="DR Congo"))
    db.commit()
    db.close()

    assert db_session.normalise_country_names() == 5
    assert db_session.normalise_country_names() == 0

    db = Session()
    stored = {c.company_name: c.country for c in db.query(Company).all()}
    db.close()
    assert stored == {
        "STP Accent": "Sao Tome and Principe",
        "CI Ivory": "Côte d'Ivoire",
        "CI Ascii": "Côte d'Ivoire",
        "CV Alias": "Cabo Verde",
        "CG Alias": "Congo",
        "DRC": "DR Congo",
    }


def test_import_canonicalises_and_matches_an_existing_alias(db):
    db.add(Company(company_name="Uni CV", country="Cape Verde", careers_url="https://unicv.example/jobs"))
    db.commit()
    head = "company_name,jse_code,careers_url,country,source_type\n"
    body = head + "Uni CV,,https://unicv.example/jobs,Cabo Verde,UNI\n"
    result = import_companies_from_csv(db, body.encode())
    assert result.created == 0
    assert result.updated == 1
    rows = db.query(Company).filter(Company.company_name == "Uni CV").all()
    assert len(rows) == 1
    assert rows[0].country == "Cabo Verde"
    assert rows[0].careers_url == "https://unicv.example/jobs"


def test_seed_country_column_has_no_alias_spellings():
    offenders: list[str] = []
    main = _SEED / "company_database_import.csv"
    with main.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            country = row["country"]
            if country in COUNTRY_ALIASES or country != canonical_country(country):
                offenders.append(f"{main.name}: {country}")
    for path in sorted((_SEED / "countries").glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.reader(handle):
                if len(row) < 8:
                    continue
                country = row[7]
                if country in COUNTRY_ALIASES:
                    offenders.append(f"{path.name}: {country}")
    assert offenders == []
