"""Organisation accounts, unpublished prices, sponsored placement, and Paystack test mode."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.migrations.employer_plans import downgrade, upgrade
from app.models.company import Company
from app.models.organisation import EmployerAuditEvent, EmployerEntitlement, EmployerInvoice
from app.models.usage_count import UsageClickDaily
from app.models.vacancy import Vacancy, VacancySource
from app.services.employer_domain import email_matches_company
from tests.conftest import make_admin, register_and_login


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _company(db_engine, name="Northwind", url="https://careers.northwind.co.za/jobs", country="South Africa"):
    session = sessionmaker(bind=db_engine)()
    try:
        company = Company(
            company_name=name, country=country, careers_url=url, official_website="https://www.northwind.co.za",
            active=True, source_type="PRIVATE",
        )
        session.add(company)
        session.commit()
        return company.id
    finally:
        session.close()


def _register_employer(client, email="org@northwind.co.za"):
    created = client.post("/api/v1/organisations/register", json={
        "email": email, "password": "Password123!", "first_name": "Aya", "last_name": "Ndlovu",
        "accepted_policy": True,
    })
    assert created.status_code == 201, created.text
    assert created.json()["user"]["role"] == "employer"
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"}).json()
    return tokens


def _verify(client, tokens, company_id, work_email="hr@northwind.co.za"):
    claim = client.post("/api/v1/organisations/claims", headers=_auth(tokens), json={
        "company_id": company_id, "work_email": work_email,
    })
    assert claim.status_code == 200, claim.text
    token = claim.json()["verification_token"]
    assert token
    verified = client.post("/api/v1/organisations/claims/verify", json={"token": token})
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"
    assert verified.json()["method"] == "domain_email"
    return verified.json()


def _post_body(**extra):
    body = {
        "title": "Graduate programme in finance",
        "opportunity_type": "graduate_programme",
        "description": "A twelve-month programme in the Johannesburg finance team, on the employer's own site.",
        "application_url": "https://careers.northwind.co.za/jobs/finance",
        "location": "Johannesburg",
    }
    body.update(extra)
    return body


def test_domain_match_uses_the_employer_site_not_a_free_inbox():
    careers = "https://careers.northwind.co.za/jobs"
    site = "https://www.northwind.co.za"
    assert email_matches_company("hr@northwind.co.za", careers, site)
    assert email_matches_company("hr@mail.northwind.co.za", careers, site)
    assert not email_matches_company("hr@gmail.com", careers, site)
    assert not email_matches_company("hr@other.co.za", careers, site)


def test_migration_is_reversible(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/employer-plans.db")
    upgrade(engine)
    upgrade(engine)
    with engine.connect() as conn:
        note = conn.execute(text(
            "SELECT owner_note FROM employer_plan_config WHERE plan_code = 'pro'"
        )).scalar()
        amount = conn.execute(text(
            "SELECT amount_zar FROM employer_plan_config WHERE plan_code = 'featured'"
        )).scalar()
    assert note == "TBD by owner"
    assert amount is None
    downgrade(engine)
    assert "employer_invoices" not in inspect(engine).get_table_names()


def test_public_plans_say_pricing_coming_soon(client):
    body = client.get("/api/v1/organisations/plans").json()
    assert body["message"] == "Pricing coming soon"
    assert body["pricing_ready"] is False
    assert body["seeker_note"]
    paid = {row["code"]: row for row in body["plans"]}
    assert paid["pro"]["amount_zar"] is None
    assert paid["pro"]["owner_note"] == "TBD by owner"
    assert paid["featured"]["price_status"] == "tbd"
    assert paid["free"]["price_status"] == "included"
    assert "authorization_url" not in body["checkout"]
    assert body["checkout"]["enabled"] is False


def test_candidate_cannot_use_employer_tools(client, db_engine):
    _, tokens = register_and_login(client)
    company_id = _company(db_engine)
    denied = client.post("/api/v1/organisations/claims", headers=_auth(tokens), json={
        "company_id": company_id, "work_email": "hr@northwind.co.za",
    })
    assert denied.status_code == 403
    assert client.get("/api/v1/organisations/clicks", headers=_auth(tokens)).status_code == 403
    assert client.post("/api/v1/organisations/checkout", headers=_auth(tokens), json={"plan_code": "pro"}).status_code == 403


def test_employer_cannot_edit_another_employers_post(client, db_engine):
    company_a = _company(db_engine)
    company_b = _company(db_engine, name="Southwind", url="https://careers.southwind.co.za/jobs")
    owner = _register_employer(client, "owner@northwind.co.za")
    _verify(client, owner, company_a)
    other = _register_employer(client, "other@southwind.co.za")
    _verify(client, other, company_b, work_email="hr@southwind.co.za")
    created = client.post("/api/v1/organisations/opportunities", headers=_auth(owner), json=_post_body())
    assert created.status_code == 201, created.text
    stolen = client.patch(
        f"/api/v1/organisations/opportunities/{created.json()['id']}",
        headers=_auth(other),
        json={"title": "Taken over"},
    )
    assert stolen.status_code == 404


def test_claim_admin_fallback_and_posts_need_approval(client, db_engine):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    mismatch = client.post("/api/v1/organisations/claims", headers=_auth(tokens), json={
        "company_id": company_id, "work_email": "person@gmail.com",
    })
    assert mismatch.status_code == 422
    waiting = client.post("/api/v1/organisations/claims/admin", headers=_auth(tokens), json={
        "company_id": company_id, "work_email": "person@gmail.com", "note": "We use a shared inbox.",
    })
    assert waiting.status_code == 200, waiting.text
    assert waiting.json()["status"] == "pending_admin"
    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    approved = client.post(
        f"/api/v1/admin/organisations/claims/{waiting.json()['id']}",
        headers=_auth(admin),
        json={"approve": True, "note": "Called the switchboard."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["method"] == "admin"
    created = client.post("/api/v1/organisations/opportunities", headers=_auth(tokens), json=_post_body())
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"
    assert created.json()["provenance"] == "employer-submitted"
    listed = client.get("/api/v1/jobs").json()
    assert created.json()["id"] not in {job["id"] for job in listed["jobs"]}
    moderated = client.post(
        f"/api/v1/admin/organisations/posts/{created.json()['id']}",
        headers=_auth(admin),
        json={"approve": True},
    )
    assert moderated.status_code == 200, moderated.text
    again = client.get("/api/v1/jobs").json()
    match = next(job for job in again["jobs"] if job["title"] == "Graduate programme in finance")
    assert match["employer_submitted"] is True
    assert match["provenance"] == "employer-submitted"
    assert match["sponsored"] is False


def test_free_post_limit(client, db_engine):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    _verify(client, tokens, company_id)
    for index in range(3):
        created = client.post("/api/v1/organisations/opportunities", headers=_auth(tokens), json=_post_body(
            title=f"Role number {index} for graduates",
            application_url=f"https://careers.northwind.co.za/jobs/{index}",
        ))
        assert created.status_code == 201, created.text
    blocked = client.post("/api/v1/organisations/opportunities", headers=_auth(tokens), json=_post_body(
        title="Role number 4 for graduates",
    ))
    assert blocked.status_code == 403


def test_off_domain_application_link_is_rejected(client, db_engine):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    _verify(client, tokens, company_id)
    rejected = client.post("/api/v1/organisations/opportunities", headers=_auth(tokens), json=_post_body(
        application_url="https://evil.example/apply",
    ))
    assert rejected.status_code == 422


def test_sponsored_rows_match_filters_and_do_not_reorder(client, db_engine):
    session = sessionmaker(bind=db_engine)()
    now = datetime.now(timezone.utc)
    try:
        sa = Company(company_name="Rank SA", country="South Africa", careers_url="https://rank.example/jobs", active=True)
        ke = Company(company_name="Rank KE", country="Kenya", careers_url="https://rank.example/ke", active=True)
        session.add_all([sa, ke])
        session.commit()
        source = VacancySource(company_id=sa.id, url="https://rank.example/jobs", ats_type="static", active=True)
        session.add(source)
        session.commit()
        newest = Vacancy(
            company_id=sa.id, source_id=source.id, title="Newest analyst", content_hash="n",
            is_open=True, first_seen_at=now, last_seen_at=now, country="South Africa",
        )
        middle = Vacancy(
            company_id=sa.id, source_id=source.id, title="Middle analyst", content_hash="m",
            is_open=True, first_seen_at=now, last_seen_at=now - timedelta(days=1), country="South Africa",
        )
        oldest = Vacancy(
            company_id=sa.id, source_id=source.id, title="Oldest analyst", content_hash="o",
            is_open=True, first_seen_at=now, last_seen_at=now - timedelta(days=2), country="South Africa",
        )
        kenya = Vacancy(
            company_id=ke.id, source_id=source.id, title="Kenya analyst", content_hash="k",
            is_open=True, first_seen_at=now, last_seen_at=now, country="Kenya",
        )
        session.add_all([newest, middle, oldest, kenya])
        session.commit()
        session.add(EmployerEntitlement(
            account_id="missing-account",
            plan_code="featured",
            status="active",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=6),
            vacancy_id=oldest.id,
        ))
        session.add(EmployerEntitlement(
            account_id="missing-account",
            plan_code="featured",
            status="active",
            starts_at=now - timedelta(days=2),
            ends_at=now + timedelta(days=6),
            vacancy_id=kenya.id,
        ))
        session.commit()
        oldest_id, kenya_id = oldest.id, kenya.id
        newest_id, middle_id = newest.id, middle.id
    finally:
        session.close()

    body = client.get("/api/v1/jobs", params={"country": "South Africa"}).json()
    ids = [job["id"] for job in body["jobs"]]
    assert ids.index(newest_id) < ids.index(middle_id) < ids.index(oldest_id)
    assert [job["id"] for job in body["sponsored"]] == [oldest_id]
    assert body["sponsored"][0]["sponsored"] is True
    assert "Sponsored" not in body["sponsored"][0]["title"]
    assert kenya_id not in ids
    assert body["sponsored_cap"] == 2
    assert "unchanged" in body["ranking_note"]
    kenya = client.get("/api/v1/jobs", params={"country": "Kenya"}).json()
    assert [job["id"] for job in kenya["sponsored"]] == [kenya_id]


def test_checkout_stays_off_without_test_keys_and_until_a_price_is_set(client, db_engine, monkeypatch):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    _verify(client, tokens, company_id)
    saved = (settings.PAYSTACK_SECRET_KEY, settings.PAYSTACK_PUBLIC_KEY)
    try:
        settings.PAYSTACK_SECRET_KEY = None
        settings.PAYSTACK_PUBLIC_KEY = None
        off = client.post("/api/v1/organisations/checkout", headers=_auth(tokens), json={"plan_code": "pro"})
        assert off.status_code == 503
        assert "authorization_url" not in off.text

        settings.PAYSTACK_SECRET_KEY = "sk_live_secret"
        settings.PAYSTACK_PUBLIC_KEY = "pk_live_public"
        live = client.post("/api/v1/organisations/checkout", headers=_auth(tokens), json={"plan_code": "pro"})
        assert live.status_code == 503
        assert "test" in live.json()["detail"].lower()

        settings.PAYSTACK_SECRET_KEY = "sk_test_secret"
        settings.PAYSTACK_PUBLIC_KEY = "pk_test_public"
        waiting = client.post("/api/v1/organisations/checkout", headers=_auth(tokens), json={"plan_code": "pro"})
        assert waiting.status_code == 409
        assert waiting.json()["detail"] == "Pricing coming soon."

        email, password = make_admin(db_engine)
        admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
        priced = client.patch("/api/v1/admin/organisations/plans/pro", headers=_auth(admin), json={
            "amount_zar": 100, "published": True,
        })
        assert priced.status_code == 200, priced.text
        assert priced.json()["amount_zar"] == 100

        def _fake_post(url, headers=None, json=None, timeout=None):
            assert url == "https://api.paystack.co/transaction/initialize"
            assert headers["Authorization"] == "Bearer sk_test_secret"
            assert "card" not in (json or {})
            request = httpx.Request("POST", url)
            return httpx.Response(200, json={
                "data": {
                    "authorization_url": "https://checkout.paystack.com/test-session",
                    "reference": json["reference"],
                },
            }, request=request)

        monkeypatch.setattr("app.payments.paystack.httpx.post", _fake_post)
        started = client.post("/api/v1/organisations/checkout", headers=_auth(tokens), json={"plan_code": "pro"})
        assert started.status_code == 200, started.text
        assert started.json()["authorization_url"].startswith("https://checkout.paystack.com/")
        assert started.json()["mode"] == "test"
        reference = started.json()["reference"]
    finally:
        settings.PAYSTACK_SECRET_KEY, settings.PAYSTACK_PUBLIC_KEY = saved

    session = sessionmaker(bind=db_engine)()
    try:
        invoice = session.query(EmployerInvoice).filter(EmployerInvoice.provider_reference == reference).one()
        assert invoice.amount_zar == 100
        assert invoice.status == "pending"
    finally:
        session.close()


def _sign(raw: bytes) -> str:
    return hmac.new(b"sk_test_secret", raw, hashlib.sha512).hexdigest()


def test_webhook_grants_once_and_a_refund_revokes(client, db_engine):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    account = _verify(client, tokens, company_id)
    saved = (settings.PAYSTACK_SECRET_KEY, settings.PAYSTACK_PUBLIC_KEY)
    settings.PAYSTACK_SECRET_KEY = "sk_test_secret"
    settings.PAYSTACK_PUBLIC_KEY = "pk_test_public"
    session = sessionmaker(bind=db_engine)()
    try:
        invoice = EmployerInvoice(
            account_id=account["id"], plan_code="pro", amount_zar=100, currency="ZAR",
            provider="paystack", provider_reference="emp_test_ref", status="pending",
        )
        session.add(invoice)
        session.commit()
        invoice_id = invoice.id
    finally:
        session.close()

    raw = json.dumps({
        "event": "charge.success",
        "data": {"reference": "emp_test_ref", "amount": 10000, "status": "success", "authorization": {"bin": "408408"}},
    }).encode()
    bad = client.post("/api/v1/organisations/webhook", content=raw, headers={"x-paystack-signature": "nope"})
    assert bad.status_code == 401
    ok = client.post("/api/v1/organisations/webhook", content=raw, headers={"x-paystack-signature": _sign(raw)})
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "paid"
    again = client.post("/api/v1/organisations/webhook", content=raw, headers={"x-paystack-signature": _sign(raw)})
    assert again.json()["status"] == "duplicate"

    session = sessionmaker(bind=db_engine)()
    try:
        rows = session.query(EmployerEntitlement).filter(EmployerEntitlement.invoice_id == invoice_id).all()
        assert len(rows) == 1
        assert rows[0].status == "active"
        stored = session.execute(text("SELECT provider_status FROM employer_payment_events")).scalar()
        assert stored == "success"
        dumped = session.execute(text("SELECT amount_zar, event_name FROM employer_payment_events")).first()
        assert dumped.amount_zar == 100
    finally:
        session.close()

    refund_raw = json.dumps({
        "event": "refund.processed",
        "data": {"status": "processed", "transaction": {"reference": "emp_test_ref", "amount": 10000}},
    }).encode()
    refunded = client.post(
        "/api/v1/organisations/webhook",
        content=refund_raw,
        headers={"x-paystack-signature": _sign(refund_raw)},
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["status"] == "refunded"
    session = sessionmaker(bind=db_engine)()
    try:
        row = session.query(EmployerEntitlement).filter(EmployerEntitlement.invoice_id == invoice_id).one()
        assert row.status == "refunded"
        invoice = session.get(EmployerInvoice, invoice_id)
        assert invoice.status == "refunded"
    finally:
        session.close()
    settings.PAYSTACK_SECRET_KEY, settings.PAYSTACK_PUBLIC_KEY = saved


def test_click_totals_are_aggregated_and_pro_only(client, db_engine):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    account = _verify(client, tokens, company_id)
    session = sessionmaker(bind=db_engine)()
    try:
        session.add(UsageClickDaily(day=datetime.now(timezone.utc).date(), target_kind="employer",
                                    target_id=company_id, clicks=4))
        session.commit()
    finally:
        session.close()
    denied = client.get("/api/v1/organisations/clicks", headers=_auth(tokens))
    assert denied.status_code == 403
    now = datetime.now(timezone.utc)
    session = sessionmaker(bind=db_engine)()
    try:
        session.add(EmployerEntitlement(
            account_id=account["id"], plan_code="pro", status="active",
            starts_at=now, ends_at=now + timedelta(days=30),
        ))
        session.commit()
    finally:
        session.close()
    allowed = client.get("/api/v1/organisations/clicks", headers=_auth(tokens))
    assert allowed.status_code == 200, allowed.text
    body = allowed.json()
    assert body["company_clicks"] == 4
    assert set(body) == {"company_clicks", "roles", "note"}
    assert body["roles"] == []
    session = sessionmaker(bind=db_engine)()
    try:
        row = session.query(EmployerAuditEvent).filter(EmployerAuditEvent.action == "clicks_read").one()
        assert row.account_id == account["id"]
    finally:
        session.close()


def test_cancel_keeps_access_until_period_end(client, db_engine):
    company_id = _company(db_engine)
    tokens = _register_employer(client)
    account = _verify(client, tokens, company_id)
    now = datetime.now(timezone.utc)
    session = sessionmaker(bind=db_engine)()
    try:
        row = EmployerEntitlement(
            account_id=account["id"], plan_code="pro", status="active",
            starts_at=now, ends_at=now + timedelta(days=30),
        )
        session.add(row)
        session.commit()
        entitlement_id = row.id
    finally:
        session.close()
    cancelled = client.post(
        f"/api/v1/organisations/entitlements/{entitlement_id}/cancel",
        headers=_auth(tokens),
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancel_at_period_end"] is True
    assert cancelled.json()["status"] == "active"
    other = _register_employer(client, "second@northwind.co.za")
    missing = client.post(
        f"/api/v1/organisations/entitlements/{entitlement_id}/cancel",
        headers=_auth(other),
    )
    assert missing.status_code in (403, 404)


def test_admin_revenue_summary(client, db_engine):
    email, password = make_admin(db_engine)
    admin = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    body = client.get("/api/v1/admin/organisations/summary", headers=_auth(admin)).json()
    assert body["currency"] == "ZAR"
    assert body["paid_zar"] == 0
    assert body["checkout"]["enabled"] is False
    assert body["sponsored_cap"] == 2
    registered, tokens = register_and_login(client, email="seeker@example.com")
    assert client.get("/api/v1/admin/organisations/summary", headers=_auth(tokens)).status_code == 403
    assert registered["user"]["role"] == "candidate"
