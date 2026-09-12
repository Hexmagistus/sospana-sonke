"""Tests for the lightweight careers-page change detector."""
from datetime import datetime, timezone

from app.models.company import Company
from app.services.link_check_service import hash_page_content, check_company_content, notify_watchers_of_change
from app.models.watch import CompanyWatch
from app.notifications.email import ConsoleEmailProvider
from tests.conftest import register_and_login


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class _FakeClient:
    def __init__(self, texts):
        self._texts = list(texts)

    def get(self, url):
        return _FakeResponse(self._texts.pop(0))


def test_hash_page_content_ignores_tags_and_whitespace():
    a = hash_page_content("<div>  Hello   <b>world</b></div>")
    b = hash_page_content("Hello world")
    assert a == b


def test_hash_page_content_differs_on_real_change():
    a = hash_page_content("<p>Vacancy: Lecturer</p>")
    b = hash_page_content("<p>Vacancy: Registrar</p>")
    assert a != b


def _company(db, **overrides):
    defaults = dict(company_name="Univ of Somewhere", source_type="UNI", country="Zambia",
                    careers_url="https://example.org/careers", active=True)
    defaults.update(overrides)
    c = Company(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_first_check_never_reports_a_change(db):
    company = _company(db)
    client = _FakeClient(["<p>First look</p>"])
    changed = check_company_content(company, client=client)
    assert changed is False
    assert company.content_hash is not None
    assert company.content_checked_at is not None
    assert company.content_changed_at is None


def test_second_check_detects_a_real_change(db):
    company = _company(db)
    check_company_content(company, client=_FakeClient(["<p>Same content</p>"]))
    changed = check_company_content(company, client=_FakeClient(["<p>Same content</p>"]))
    assert changed is False  # identical page: no change
    changed = check_company_content(company, client=_FakeClient(["<p>New vacancy posted!</p>"]))
    assert changed is True
    assert company.content_changed_at is not None


def test_no_careers_url_is_a_no_op(db):
    company = _company(db, careers_url=None)
    changed = check_company_content(company, client=_FakeClient([]))
    assert changed is False
    assert company.content_hash is None


def test_notify_watchers_of_change_emails_matching_watchers(db, client):
    ConsoleEmailProvider.outbox.clear()
    reg, _ = register_and_login(client, email="watcher@example.com")
    company = _company(db)
    db.add(CompanyWatch(user_id=reg["id"], company_id=company.id, active=True))
    db.commit()

    company.content_hash = "abc123"
    sent = notify_watchers_of_change(db, company)
    assert sent == 1
    assert any(m["to"] == "watcher@example.com" for m in ConsoleEmailProvider.outbox)


def test_notify_watchers_of_change_is_idempotent_per_hash(db, client):
    ConsoleEmailProvider.outbox.clear()
    reg, _ = register_and_login(client, email="watcher2@example.com")
    company = _company(db)
    db.add(CompanyWatch(user_id=reg["id"], company_id=company.id, active=True))
    db.commit()

    company.content_hash = "same-hash"
    first = notify_watchers_of_change(db, company)
    second = notify_watchers_of_change(db, company)
    assert first == 1
    assert second == 0  # same hash -> same related_id -> no repeat email

    company.content_hash = "different-hash"
    third = notify_watchers_of_change(db, company)
    assert third == 1  # a genuinely new change fires again
