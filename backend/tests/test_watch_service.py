"""Tests for notify-me watch subscriptions and matching."""
import pytest
from fastapi import HTTPException

from app.models.company import Company
from app.models.watch import CompanyWatch
from app.services.watch_service import create_watch, delete_watch, matches, find_watchers_for_company
from tests.conftest import register_and_login


def _company(db, **overrides):
    defaults = dict(company_name="Univ of Somewhere", source_type="UNI", country="Zambia",
                    careers_url="https://example.org/careers", active=True)
    defaults.update(overrides)
    c = Company(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _user_id(client):
    reg, _ = register_and_login(client)
    return reg["id"]


def test_create_watch_requires_a_scope(db):
    with pytest.raises(HTTPException) as exc:
        create_watch(db, user_id="u1", company_id=None, country=None, source_type=None)
    assert exc.value.status_code == 400


def test_create_watch_unknown_company_404s(db):
    with pytest.raises(HTTPException) as exc:
        create_watch(db, user_id="u1", company_id="does-not-exist", country=None, source_type=None)
    assert exc.value.status_code == 404


def test_resubscribing_reactivates_instead_of_duplicating(db, client):
    user_id = _user_id(client)
    w1 = create_watch(db, user_id=user_id, company_id=None, country="Zambia", source_type=None)
    w1.active = False
    db.commit()
    w2 = create_watch(db, user_id=user_id, company_id=None, country="Zambia", source_type=None)
    assert w2.id == w1.id
    assert w2.active is True
    assert db.query(CompanyWatch).filter(CompanyWatch.user_id == user_id).count() == 1


def test_delete_watch_only_owner(db, client):
    user_id = _user_id(client)
    other_user_id = "someone-else"
    watch = create_watch(db, user_id=user_id, company_id=None, country="Zambia", source_type=None)
    with pytest.raises(HTTPException) as exc:
        delete_watch(db, user_id=other_user_id, watch_id=watch.id)
    assert exc.value.status_code == 404
    delete_watch(db, user_id=user_id, watch_id=watch.id)
    assert db.get(CompanyWatch, watch.id) is None


def test_matches_company_scoped_watch(db):
    company = _company(db)
    other = _company(db, company_name="Different University")
    watch = CompanyWatch(user_id="u1", company_id=company.id)
    assert matches(watch, company) is True
    assert matches(watch, other) is False


def test_matches_country_and_category_scoped_watch(db):
    company = _company(db, country="Zambia", source_type="UNI")
    wrong_country = _company(db, company_name="X", country="Kenya", source_type="UNI")
    wrong_type = _company(db, company_name="Y", country="Zambia", source_type="SOE")

    watch = CompanyWatch(user_id="u1", country="Zambia", source_type="UNI")
    assert matches(watch, company) is True
    assert matches(watch, wrong_country) is False
    assert matches(watch, wrong_type) is False

    # Country-only watch (any category) still matches.
    country_only = CompanyWatch(user_id="u1", country="Zambia")
    assert matches(country_only, wrong_type) is True
    assert matches(country_only, wrong_country) is False


def test_find_watchers_for_company_ignores_inactive(db):
    company = _company(db)
    active = CompanyWatch(user_id="u1", company_id=company.id, active=True)
    inactive = CompanyWatch(user_id="u2", company_id=company.id, active=False)
    db.add_all([active, inactive])
    db.commit()
    found = find_watchers_for_company(db, company)
    assert [w.user_id for w in found] == ["u1"]
