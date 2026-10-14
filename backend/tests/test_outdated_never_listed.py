"""Outdated roles never reach the site.

A role is outdated when its closing day has ended, when the scanner or the
weekly clean-up has closed it (is_open false, lifecycle REMOVED), or when it
has not been seen on the employer's own site for more than 7 days. Such rows
must not be listed or counted, and the scanner must not store a brand-new
posting whose closing day has already passed.
"""
from datetime import date, datetime, timedelta, timezone

import httpx

from app.models.company import Company
from app.models.vacancy import Vacancy
from app.services import scan_service
from app.services.opportunity_expiry import (
    closing_value_has_passed, is_publicly_listed, public_role_clauses, sa_today,
)
from app.services.scan_service import ensure_source, scan_source


def _company(db, name="Acme", url="https://boards.greenhouse.io/acme"):
    c = Company(company_name=name, careers_url=url, scraping_status="pending", country="South Africa")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _row(db, company, title, **kw):
    now = datetime.now(timezone.utc)
    fields = dict(company_id=company.id, source_id="src-x", title=title, content_hash=title,
                  is_open=True, lifecycle_status="ACTIVE", first_seen_at=now, last_seen_at=now)
    fields.update(kw)
    v = Vacancy(**fields)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _seed_mix(db):
    c = _company(db)
    today = sa_today()
    now = datetime.now(timezone.utc)
    rows = {
        "fresh": _row(db, c, "Fresh Role"),
        "closes_today": _row(db, c, "Closes Today", closing_date=today),
        "past_close": _row(db, c, "Past Closing", closing_date=today - timedelta(days=1)),
        "removed": _row(db, c, "Removed Role", is_open=False, lifecycle_status="REMOVED"),
        "removed_flag_only": _row(db, c, "Removed Flag Only", lifecycle_status="REMOVED"),
        "stale": _row(db, c, "Not Seen Eight Days", last_seen_at=now - timedelta(days=8)),
        "seen_six_days": _row(db, c, "Seen Six Days Ago", last_seen_at=now - timedelta(days=6)),
    }
    return c, rows


def test_public_rule_hides_every_kind_of_outdated_row(db):
    _, rows = _seed_mix(db)
    shown = {v.id for v in db.query(Vacancy).filter(*public_role_clauses()).all()}
    assert shown == {rows["fresh"].id, rows["closes_today"].id, rows["seen_six_days"].id}
    for key, v in rows.items():
        assert is_publicly_listed(v) == (v.id in shown), key


def test_public_jobs_api_lists_and_counts_no_outdated_rows(client, db):
    _, rows = _seed_mix(db)
    body = client.get("/api/v1/jobs").json()
    ids = {job["id"] for job in body["jobs"]}
    assert ids == {rows["fresh"].id, rows["closes_today"].id, rows["seen_six_days"].id}
    assert body["matched"] == 3
    for key in ("past_close", "removed", "removed_flag_only", "stale"):
        assert client.get(f"/api/v1/jobs/{rows[key].id}").status_code in (404, 410), key


def test_closing_value_parsing():
    today = date(2026, 10, 14)
    assert closing_value_has_passed(date(2026, 10, 13), today)
    assert not closing_value_has_passed(date(2026, 10, 14), today)
    assert closing_value_has_passed("2026-10-01", today)
    assert closing_value_has_passed(datetime(2026, 10, 1, 9, 0), today)
    assert not closing_value_has_passed(None, today)
    assert not closing_value_has_passed("", today)
    assert not closing_value_has_passed("soon", today)


def _greenhouse(jobs):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if "boards-api.greenhouse.io" in url:
            return httpx.Response(200, json={"jobs": jobs})
        return httpx.Response(404)
    return handler


def test_scanner_never_stores_a_new_posting_that_has_already_closed(db, monkeypatch):
    c = _company(db)
    src = ensure_source(db, c)
    yesterday = sa_today() - timedelta(days=1)
    real_adapter_for = scan_service.adapter_for

    class _WithClosing:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def normalize(self, raw, **kw):
            fields = self._inner.normalize(raw, **kw)
            if "Expired" in (fields.get("title") or ""):
                fields["closing_date"] = yesterday
            return fields

    monkeypatch.setattr(scan_service, "adapter_for", lambda kind: _WithClosing(real_adapter_for(kind)))
    jobs = [
        {"id": 1, "title": "Live Role", "location": {"name": "Johannesburg"},
         "absolute_url": "https://boards.greenhouse.io/acme/jobs/1", "content": "<p>Open</p>"},
        {"id": 2, "title": "Expired Role", "location": {"name": "Durban"},
         "absolute_url": "https://boards.greenhouse.io/acme/jobs/2", "content": "<p>Closed</p>"},
    ]
    with httpx.Client(transport=httpx.MockTransport(_greenhouse(jobs))) as http:
        report = scan_source(db, src, client=http)
    titles = {v.title for v in db.query(Vacancy).filter(Vacancy.company_id == c.id).all()}
    assert titles == {"Live Role"}
    assert report.created == 1
    assert report.skipped_expired == 1


def test_boot_adds_mapped_columns_before_upgrades_query_the_model():
    """Every deploy from 13 Oct failed: an upgrade queried Vacancy before
    quality_flags existed. Columns must be added first."""
    import inspect as _inspect
    from app.db import session
    src = _inspect.getsource(session.init_db)
    assert src.index("_add_new_columns()") < src.index("upgrade_verified_programmes(engine)")


def test_plan_seed_passes_a_real_boolean_for_published():
    import inspect as _inspect
    from app.db.migrations import employer_plans
    assert '"published": bool(published)' in _inspect.getsource(employer_plans._seed_plan)


def test_purge_does_nothing_unless_switched_on(db, monkeypatch):
    from app.services.opportunity_purge import purge_expired_opportunities
    monkeypatch.delenv("OPPORTUNITY_PURGE_ENABLED", raising=False)
    c = _company(db)
    v = _row(db, c, "Closed Role", is_open=False, lifecycle_status="REMOVED")
    out = purge_expired_opportunities(db)
    assert out["deleted"] == 0 and out.get("disabled") is True
    assert db.get(Vacancy, v.id) is not None
