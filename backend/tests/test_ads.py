"""Advertiser spot applications: minimum amount, validation, rate limit, admin approval.
Ads show only on the login page, in four spots LG1-LG4."""
from tests.conftest import make_admin, register_and_login

URL = "/api/v1/ads/applications"
GOOD = {
    "business_name": "Mabena Plumbing",
    "contact_email": "owner@mabena.example",
    "website": "https://mabena.example",
    "ad_text": "Plumbing across Gauteng",
    "amount_usd_per_day": "1.00",
    "days": 7,
}


def _admin(client, db_engine):
    email, password = make_admin(db_engine)
    t = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_no_ads_are_shown_until_one_is_approved(client):
    r = client.get("/api/v1/ads/slots")
    assert r.status_code == 200 and r.json() == []


def test_apply_at_the_minimum_stores_a_pending_application(client, db_engine):
    r = client.post(URL, json=GOOD)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["total_usd"] == "7.00"
    assert "Nothing has been charged" in body["message"]
    assert client.get("/api/v1/ads/slots").json() == []  # pending is never published
    rows = client.get("/api/v1/ads/admin/applications", headers=_admin(client, db_engine)).json()
    assert len(rows) == 1 and rows[0]["status"] == "pending"
    assert rows[0]["contact_email"] == "owner@mabena.example"


def test_amount_below_one_dollar_a_day_is_rejected_server_side(client):
    for bad in ("0.99", "0", "-5", "0.5"):
        r = client.post(URL, json={**GOOD, "amount_usd_per_day": bad})
        assert r.status_code == 422, bad
        assert "minimum is $1 per day" in r.text


def test_amount_above_one_dollar_is_accepted_and_totalled(client):
    r = client.post(URL, json={**GOOD, "amount_usd_per_day": "2.50", "days": 10})
    assert r.status_code == 201
    assert r.json()["total_usd"] == "25.00"


def test_validation(client):
    cases = [
        {"contact_email": "not-an-email"},
        {"website": "javascript:alert(1)"},
        {"website": "https://user:pw@x.example"},
        {"website": "nodots"},
        {"ad_text": "x" * 121},
        {"ad_text": ""},
        {"business_name": ""},
        {"days": 0},
        {"days": 400},
        {"requested_slot": "L11"},
        {"requested_slot": "X1"},
        {"requested_slot": "LG5"},
        {"requested_slot": "LG0"},
        {"amount_usd_per_day": "abc"},
        {"amount_usd_per_day": "10001"},
    ]
    for patch in cases:
        r = client.post(URL, json={**GOOD, **patch})
        assert r.status_code == 422, patch


def test_website_without_scheme_gets_https_and_text_is_one_line(client, db_engine):
    r = client.post(URL, json={**GOOD, "website": "mabena.example", "ad_text": "Line one\nline   two", "requested_slot": "LG3"})
    assert r.status_code == 201
    row = client.get("/api/v1/ads/admin/applications", headers=_admin(client, db_engine)).json()[0]
    assert row["website"] == "https://mabena.example"
    assert row["ad_text"] == "Line one line two"
    assert row["requested_slot"] == "LG3"


def test_pending_cap_per_email_holds_without_the_ip_limiter(client):
    for i in range(3):
        assert client.post(URL, json=GOOD).status_code == 201
    r = client.post(URL, json=GOOD)
    assert r.status_code == 429
    assert client.post(URL, json={**GOOD, "contact_email": "other@mabena.example"}).status_code == 201


def test_per_ip_rate_limit_applies_when_enabled(client):
    from app.core.rate_limit import limiter
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [client.post(URL, json={**GOOD, "contact_email": f"u{i}@mabena.example"}).status_code for i in range(7)]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert codes[:5] == [201] * 5
    assert 429 in codes[5:]


def test_admin_endpoints_need_an_admin(client):
    assert client.get("/api/v1/ads/admin/applications").status_code in (401, 403)
    _, tokens = register_and_login(client, email="cand@example.com")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/api/v1/ads/admin/applications", headers=h).status_code == 403


def test_approval_publishes_in_the_slot_and_reject_does_not(client, db_engine):
    h = _admin(client, db_engine)
    a = client.post(URL, json={**GOOD, "requested_slot": "LG2"}).json()["id"]
    b = client.post(URL, json={**GOOD, "contact_email": "b@x.example", "business_name": "Bee Co"}).json()["id"]

    # an explorer-era or unknown spot is refused when the admin names it
    for bad in ("L2", "R10", "LG9"):
        r = client.patch(f"/api/v1/ads/admin/applications/{b}", json={"status": "approved", "slot_key": bad}, headers=h)
        assert r.status_code == 422, bad

    r = client.patch(f"/api/v1/ads/admin/applications/{a}", json={"status": "approved"}, headers=h)
    assert r.status_code == 200 and r.json()["slot_key"] == "LG2" and r.json()["ends_at"]
    shown = client.get("/api/v1/ads/slots").json()
    assert shown == [{"slot_key": "LG2", "business_name": "Mabena Plumbing",
                      "ad_text": "Plumbing across Gauteng", "website": "https://mabena.example"}]

    # a second ad cannot take a running slot
    r = client.patch(f"/api/v1/ads/admin/applications/{b}", json={"status": "approved", "slot_key": "LG2"}, headers=h)
    assert r.status_code == 409
    r = client.patch(f"/api/v1/ads/admin/applications/{b}", json={"status": "rejected", "admin_note": "off topic"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert len(client.get("/api/v1/ads/slots").json()) == 1

    # un-approving takes it down again
    client.patch(f"/api/v1/ads/admin/applications/{a}", json={"status": "pending"}, headers=h)
    assert client.get("/api/v1/ads/slots").json() == []


def test_only_four_login_spots_exist_and_approval_fills_free_ones(client, db_engine):
    h = _admin(client, db_engine)
    ids = [
        client.post(URL, json={**GOOD, "contact_email": f"o{i}@x.example", "business_name": f"Biz {i}"}).json()["id"]
        for i in range(5)
    ]
    slots = []
    for i in ids[:4]:
        r = client.patch(f"/api/v1/ads/admin/applications/{i}", json={"status": "approved"}, headers=h)
        assert r.status_code == 200
        slots.append(r.json()["slot_key"])
    assert slots == ["LG1", "LG2", "LG3", "LG4"]
    # a fifth cannot be placed while all four run
    r = client.patch(f"/api/v1/ads/admin/applications/{ids[4]}", json={"status": "approved"}, headers=h)
    assert r.status_code == 409
    assert [a["slot_key"] for a in client.get("/api/v1/ads/slots").json()] == ["LG1", "LG2", "LG3", "LG4"]


def test_old_explorer_spot_keys_still_work(client, db_engine):
    """A cached old page may still send L1-L10/R1-R10; rows stored with them are placed on login."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy.orm import sessionmaker
    from app.models.ad import AdApplication
    r = client.post(URL, json={**GOOD, "requested_slot": "L7"})
    assert r.status_code == 201
    h = _admin(client, db_engine)
    row = client.get("/api/v1/ads/admin/applications", headers=h).json()[0]
    assert row["requested_slot"] is None  # any login spot
    # an ad approved in the explorer era (legacy slot_key) is shown in a free login spot
    S = sessionmaker(bind=db_engine)
    s = S()
    legacy = s.get(AdApplication, row["id"])
    legacy.status, legacy.slot_key = "approved", "R3"
    legacy.starts_at = datetime.now(timezone.utc) - timedelta(days=1)
    legacy.ends_at = datetime.now(timezone.utc) + timedelta(days=1)
    s.commit()
    s.close()
    assert [a["slot_key"] for a in client.get("/api/v1/ads/slots").json()] == ["LG1"]


def test_an_ad_past_its_end_date_is_not_shown(client, db_engine):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy.orm import sessionmaker
    from app.models.ad import AdApplication
    h = _admin(client, db_engine)
    a = client.post(URL, json=GOOD).json()["id"]
    client.patch(f"/api/v1/ads/admin/applications/{a}", json={"status": "approved", "slot_key": "LG1"}, headers=h)
    assert len(client.get("/api/v1/ads/slots").json()) == 1
    S = sessionmaker(bind=db_engine)
    s = S()
    row = s.get(AdApplication, a)
    row.ends_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    s.commit()
    s.close()
    assert client.get("/api/v1/ads/slots").json() == []
