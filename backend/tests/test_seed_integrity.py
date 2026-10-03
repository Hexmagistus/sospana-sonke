"""The seed CSV is re-imported on every boot (AUTO_SEED), so it must agree with
data fixes made in the database: categories, branded careers links, retired duplicates."""
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from app.models.company import Company
from app.models.vacancy import VacancySource
from app.services.csv_import import import_companies_from_csv

_SEED = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"


def _rows():
    with _SEED.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def test_seed_files_universities_as_uni_and_teaching_hospitals_as_hospital():
    for r in _rows():
        name, kind = r["company_name"], r["source_type"].upper()
        if not re.search(r"universit|universidad", name, re.I) or re.search(r"university college", name, re.I):
            continue
        want = "HOSPITAL" if re.search(r"hospital|medical cent", name, re.I) else None
        if want:
            assert kind == "HOSPITAL", name
        else:
            assert kind != "COLLEGE", f"{name} is a university but the seed files it as COLLEGE"


def test_seed_does_not_carry_the_punctuation_variants_retired_as_duplicates():
    retired = {
        ("Cabo Verde", "Universidade de Cabo Verde Uni-CV"), ("Eswatini", "Southern Africa Nazarene University (SANU)"),
        ("Eswatini", "Limkokwing University of Creative Technology (Eswatini)"),
        ("Malawi", "DMI-St John the Baptist University"),
        ("Zambia", "National Institute of Public Administration (NIPA)"),
        ("Zambia", "Northern Technical College NORTEC"),
    }
    assert not ({(r["country"], r["company_name"]) for r in _rows()} & retired)


def test_seed_carries_branded_careers_links_not_ats_urls():
    urls = {(r["company_name"], r["country"]): r["careers_url"] for r in _rows()}
    assert urls[("Cleveland Clinic", "United States")] == "https://jobs.clevelandclinic.org/job-search-results/"
    assert urls[("Maersk", "Denmark")] and "myworkdayjobs" not in urls[("Maersk", "Denmark")]


def _head():
    return "company_name,jse_code,careers_url,scraping_status,active,country,source_type\n"


def test_reimport_keeps_soft_deleted_duplicate_deleted_and_creates_nothing(db):
    live = Company(company_name="Uni Alpha", country="Eswatini", source_type="UNI", active=True)
    gone = Company(company_name="Uni Alpha", country="Eswatini", source_type="UNI", active=True,
                   deleted_at=datetime.now(timezone.utc))
    variant = Company(company_name="Uni Alpha (Eswatini)", country="Eswatini", source_type="COLLEGE", active=True,
                      deleted_at=datetime.now(timezone.utc))
    db.add_all([gone, live, variant])
    db.commit()
    body = _head() + (
        "Uni Alpha,,https://alpha.example/careers,pending,true,Eswatini,UNI\n"
        "Uni Alpha (Eswatini),,,pending,true,Eswatini,COLLEGE\n"
    )
    for _ in range(2):
        result = import_companies_from_csv(db, body.encode())
        assert result.created == 0
    db.expire_all()
    assert db.query(Company).count() == 3
    assert db.get(Company, live.id).careers_url == "https://alpha.example/careers"  # live row is the one refreshed
    assert db.get(Company, live.id).deleted_at is None
    assert db.get(Company, gone.id).deleted_at is not None
    assert db.get(Company, variant.id).deleted_at is not None


def test_reimport_sets_category_and_url_from_seed_and_leaves_vacancy_sources_alone(db):
    c = Company(company_name="Beta Clinic", country="United States", source_type="COLLEGE", active=True,
                careers_url="https://beta.wd1.myworkdayjobs.com/x")
    db.add(c)
    db.commit()
    src = VacancySource(company_id=c.id, url="https://beta.wd1.myworkdayjobs.com/x", ats_type="workday")
    db.add(src)
    db.commit()
    before = (src.url, src.ats_type, src.last_status)
    body = _head() + "Beta Clinic,,https://jobs.beta.example/search,pending,true,United States,HOSPITAL\n"
    import_companies_from_csv(db, body.encode())
    db.expire_all()
    c2 = db.get(Company, c.id)
    assert (c2.source_type, c2.careers_url) == ("HOSPITAL", "https://jobs.beta.example/search")
    s2 = db.query(VacancySource).filter(VacancySource.company_id == c.id).one()
    assert (s2.url, s2.ats_type, s2.last_status) == before


def test_seed_keys_are_unique_and_a_second_import_creates_nothing(db):
    """The importer keys on (name, JSE code, country). A repeated key would make two seed rows fight
    over one company, and a key the DB already holds must update that row, never add another."""
    from app.services.country_names import canonical_country
    keys = [(" ".join(r["company_name"].lower().split()), (r["jse_code"] or "").strip().upper(),
             canonical_country((r["country"] or "South Africa").strip() or "South Africa")) for r in _rows()]
    assert len(keys) == len(set(keys))
    body = _SEED.read_bytes()
    first = import_companies_from_csv(db, body)
    assert first.created == len(keys) and first.errors == []
    second = import_companies_from_csv(db, body)
    assert second.created == 0 and second.updated == len(keys)
    assert db.query(Company).count() == len(keys)


def test_seed_carries_the_url_fixes_made_in_the_database():
    urls = {(r["company_name"], r["country"]): r["careers_url"] for r in _rows()}
    assert urls[("Central University of Technology (CUT)", "South Africa")] == "https://cut.simplify.hr/"
    assert urls[("North-West University (NWU)", "South Africa")] == "https://nwu.ci.hr/applicant/index.php"
    assert urls[("Walter Sisulu University (WSU)", "South Africa")] == "https://waltersisulucareers.ci.hr/applicant/index.php"
    assert urls[("Brand South Africa", "South Africa")] == "https://www.brandsouthafrica.com/vacancies/"
    assert urls[("Microsoft", "United States")] == "https://careers.microsoft.com/v2/global/en/home.html"


def test_seed_carries_pending_url_fixes_and_db_only_employers():
    rows = {(r["company_name"], r["country"]): r for r in _rows()}
    nhbrc = rows[("National Home Builders Registration Council", "South Africa")]
    assert nhbrc["careers_url"] == "https://www.nhbrc.org.za/career/"
    sapo = rows[("South African Post Office (SAPO)", "South Africa")]
    assert sapo["careers_url"] == "https://www.postoffice.co.za/careers.html" and sapo["active"] == "true"
    assert rows[("Passenger Rail Agency of South Africa (PRASA)", "South Africa")]["careers_url"].startswith("https://prasa.com/")
    # Africa expansion batches 1-4, US batches 5-13 and the DB-only SA state-owned rows
    for key in [("Intercare Group", "South Africa"), ("Carbon (Nigeria)", "Nigeria"), ("Instabug", "Egypt"),
                ("Bill & Melinda Gates Foundation", "United States"), ("Transnet Freight Rail", "South Africa"),
                ("Electoral Commission of South Africa (IEC)", "South Africa")]:
        assert key in rows, key
    assert rows[("Instabug", "Egypt")]["careers_url"] == "https://www.luciq.ai/careers"  # live value, no :443


def test_seed_urls_have_no_explicit_default_port():
    for r in _rows():
        assert ":443/" not in r["careers_url"] and not r["careers_url"].endswith(":443"), r["company_name"]
