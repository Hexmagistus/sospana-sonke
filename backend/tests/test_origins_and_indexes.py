"""CORS origin pinning and the additive hot-query indexes."""
import re

from sqlalchemy import inspect

from app.core.origins import VERCEL_ORIGIN_REGEX, origin_allowed
from app.db import session as db_session
from app.main import app
from starlette.middleware.gzip import GZipMiddleware


def test_vercel_origins_allow_production_and_team_previews_only():
    assert origin_allowed("https://sospana-sonke.vercel.app")
    assert origin_allowed("https://sospana-sonke-git-main-hexmagistus1.vercel.app")
    # re.match (what CORSMiddleware uses) must also reject these, so the
    # pattern itself has to be end-anchored, not only fullmatch().
    pat = re.compile(VERCEL_ORIGIN_REGEX)
    assert pat.match("https://sospana-sonke.vercel.app")
    assert pat.match("https://sospana-sonke.vercel.app.evil.com") is None
    assert pat.match("https://sospana-sonke-evil.vercel.app") is None
    assert pat.match("https://evil-sospana-sonke.vercel.app") is None
    assert pat.match("http://sospana-sonke.vercel.app") is None
    assert not origin_allowed("https://sospana-sonke.vercel.app.evil.com")


def test_app_cors_regex_is_the_pinned_pattern():
    regexes = []
    for middleware in app.user_middleware:
        if getattr(middleware, "kwargs", None) and "allow_origin_regex" in middleware.kwargs:
            regexes.append(middleware.kwargs["allow_origin_regex"])
    assert regexes == [VERCEL_ORIGIN_REGEX]


def test_gzip_wraps_responses():
    assert any(m.cls is GZipMiddleware for m in app.user_middleware)


def test_hot_query_indexes_are_created_and_idempotent(db_engine, monkeypatch):
    monkeypatch.setattr(db_session, "engine", db_engine)
    db_session._ensure_indexes()
    db_session._ensure_indexes()
    company_indexes = {ix["name"] for ix in inspect(db_engine).get_indexes("companies")}
    vacancy_indexes = {ix["name"] for ix in inspect(db_engine).get_indexes("vacancies")}
    assert "ix_companies_country_type" in company_indexes
    assert "ix_companies_deleted_at" in company_indexes
    assert "ix_vacancies_open_closing" in vacancy_indexes
