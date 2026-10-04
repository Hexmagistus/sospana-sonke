"""Tests for source-change admin alerts and interview preparation."""
import httpx

from tests.conftest import register_and_login
from app.core import security
from app.models.user import User
from app.models.company import Company
from app.models.notification import Notification
from app.services.scan_service import ensure_source, scan_source


def _admin(db, email="admin@x.co"):
    u = User(email=email, password_hash=security.hash_password("x"), first_name="A", last_name="D",
             role="admin", email_verified=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _company(db, url="https://boards.greenhouse.io/acme"):
    c = Company(company_name="Acme", careers_url=url)
    db.add(c); db.commit(); db.refresh(c)
    return c


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_source_failure_alerts_admin(db):
    _admin(db)
    src = ensure_source(db, _company(db))

    def handler(request):
        if str(request.url).endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(500, text="boom")

    for _ in range(3):
        with _client(handler) as c:
            scan_source(db, src, client=c)

    alerts = db.query(Notification).filter(Notification.type == "source_alert").all()
    assert len(alerts) == 1  # edge-triggered once at the threshold (3)
    assert "failing" in alerts[0].title.lower() or "acme" in alerts[0].title.lower()


def test_structure_change_alerts_admin(db):
    _admin(db)
    src = ensure_source(db, _company(db))
    jobs = [{"id": 1, "title": "Ops Manager", "absolute_url": "u1", "content": "<p>role</p>"}]

    def make(js):
        def handler(request):
            if str(request.url).endswith("robots.txt"):
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            return httpx.Response(200, json={"jobs": js})
        return handler

    with _client(make(jobs)) as c:      # first scan: 1 vacancy
        scan_source(db, src, client=c)
    with _client(make([])) as c:        # second scan: 0 -> structure change
        scan_source(db, src, client=c)

    alerts = db.query(Notification).filter(Notification.type == "source_alert").all()
    assert any("changed" in a.title.lower() for a in alerts)


# ---- interview prep ----

def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_interview_prep_from_a_match_is_gone(client):
    _, tokens = register_and_login(client)
    for method in (client.post, client.get):
        r = method("/api/v1/matches/some-id/interview-prep", headers=_auth(tokens))
        assert r.status_code == 410
