"""Tests for source-change admin alerts and interview preparation."""
from datetime import datetime, timezone

import httpx

from tests.conftest import register_and_login
from app.core import security
from app.models.user import User
from app.models.company import Company
from app.models.notification import Notification
from app.models.vacancy import Vacancy, VacancyRequirement
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


def _seed_and_match(client, tokens, db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine); s = S()
    try:
        c = Company(company_name="Acme Logistics", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title="Operations Manager", location="Johannesburg",
                    description="SQL needed.", content_hash="h1", is_open=True,
                    first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text="Minimum of 5 years experience required",
                                 kind="hard", category="experience"))
        s.commit()
    finally:
        s.close()
    h = _auth(tokens)
    client.put("/api/v1/profile", headers=h, json={"years_experience": 6,
               "desired_occupations": ["Operations Manager"], "industries": ["logistics"],
               "preferred_locations": ["Johannesburg"]})
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})
    client.post("/api/v1/matches/run", headers=h)
    return client.get("/api/v1/matches", headers=h).json()[0]["id"]


def test_interview_prep_generation(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _seed_and_match(client, tokens, db_engine)

    gen = client.post(f"/api/v1/matches/{match_id}/interview-prep", headers=_auth(tokens))
    assert gen.status_code == 201, gen.text
    content = gen.json()["content"]
    assert any("Operations Manager" in q for q in content["questions"])
    assert any("5 years experience" in q for q in content["questions"])   # from the requirement
    assert content["talking_points"] and content["tips"]

    got = client.get(f"/api/v1/matches/{match_id}/interview-prep", headers=_auth(tokens))
    assert got.status_code == 200 and got.json()["id"] == gen.json()["id"]


def test_interview_prep_ownership(client, db_engine):
    _, ta = register_and_login(client, email="a@example.com")
    _, tb = register_and_login(client, email="b@example.com")
    match_id = _seed_and_match(client, ta, db_engine)
    client.post(f"/api/v1/matches/{match_id}/interview-prep", headers=_auth(ta))
    # B cannot generate from A's match nor read A's prep
    assert client.post(f"/api/v1/matches/{match_id}/interview-prep", headers=_auth(tb)).status_code == 404
    assert client.get(f"/api/v1/matches/{match_id}/interview-prep", headers=_auth(tb)).status_code == 404
