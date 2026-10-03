"""GET /companies/facets: per-country counted employers and open vacancies."""
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from tests.conftest import register_and_login


def _h(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _company(s, name, country, careers="https://x.example/careers", active=True):
    c = Company(company_name=name, country=country, source_type="PRIVATE",
                careers_url=careers, active=active)
    s.add(c)
    s.commit()
    s.refresh(c)
    return c


def _source(s, company, *, status=None, parser=None, success=True):
    src = VacancySource(company_id=company.id, url="https://x.example/jobs",
                        scraper_status=status, parser_used=parser,
                        last_success_at=datetime.now(timezone.utc) if success else None)
    s.add(src)
    s.commit()
    s.refresh(src)
    return src


def _vacancy(s, company, src, title, *, is_open=True, lifecycle=None, deleted=False):
    now = datetime.now(timezone.utc)
    v = Vacancy(company_id=company.id, source_id=src.id, title=title,
                application_url="https://x.example/apply", content_hash="h-" + title,
                is_open=is_open, lifecycle_status=lifecycle, first_seen_at=now, last_seen_at=now,
                deleted_at=now if deleted else None)
    s.add(v)
    s.commit()


def test_facets_has_counted_and_open_vacancies_per_country(client, db_engine):
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        a = _company(s, "Alpha", "South Africa")            # holds 2 open rows -> counted
        b = _company(s, "Bravo", "South Africa")            # structured parser, real zero -> counted
        c = _company(s, "Charlie", "South Africa")          # static empty read -> NOT counted
        d = _company(s, "Delta", "South Africa")            # never scanned -> NOT counted
        e = _company(s, "Echo", "Kenya")                    # only closed rows -> NOT counted
        f = _company(s, "Foxtrot", "Ivory Coast")           # old spelling merges into Côte d'Ivoire
        gone = _company(s, "Golf", "South Africa")
        gone.deleted_at = datetime.now(timezone.utc)
        s.commit()

        sa = _source(s, a, status="SUCCESS", parser="greenhouse")
        _vacancy(s, a, sa, "Open 1")
        _vacancy(s, a, sa, "Open 2", lifecycle="ACTIVE")
        _vacancy(s, a, sa, "Closed", is_open=False)
        _vacancy(s, a, sa, "Expired", lifecycle="EXPIRED")
        _vacancy(s, a, sa, "Removed row", deleted=True)
        _source(s, b, status="NO_VACANCIES", parser="lever")
        _source(s, c, status="NO_VACANCIES", parser="static")
        se = _source(s, e, status="SUCCESS", parser="static", success=False)
        _vacancy(s, e, se, "Old", is_open=False)
        sf = _source(s, f, status="SUCCESS", parser="workday")
        _vacancy(s, f, sf, "Abidjan job")
        del d, gone
    finally:
        s.close()

    _, tokens = register_and_login(client)
    r = client.get("/api/v1/companies/facets", headers=_h(tokens))
    assert r.status_code == 200, r.text
    data = r.json()
    # Existing keys are untouched.
    assert data["country_counts"]["South Africa"] == 4
    assert data["country_with_links"]["South Africa"] == 4
    # Alpha (open rows) and Bravo (structured zero) are counted; Charlie and Delta are not.
    assert data["country_counted"]["South Africa"] == 2
    assert data["country_open_vacancies"]["South Africa"] == 2
    assert data["country_counted"]["Kenya"] == 0
    assert data["country_open_vacancies"]["Kenya"] == 0
    assert data["country_counted"]["Côte d'Ivoire"] == 1
    assert data["country_open_vacancies"]["Côte d'Ivoire"] == 1
    # Every counted country is a listed country: nothing invented.
    assert set(data["country_counted"]) <= set(data["country_counts"])
    assert sum(data["country_open_vacancies"].values()) == 3


def test_facets_counted_requires_login(client):
    assert client.get("/api/v1/companies/facets").status_code in (401, 403)
