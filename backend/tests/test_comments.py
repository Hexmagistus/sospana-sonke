"""Community tips under employer links."""
from tests.conftest import register_and_login
from app.models.company import Company

API = "/api/v1"


def _h(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _company(db_session_factory=None):
    pass


def _mk(client):
    from app.db.session import get_db
    db = next(client.app.dependency_overrides[get_db]())
    c = Company(company_name="Acme", country="South Africa", careers_url="https://acme.example/careers")
    db.add(c)
    db.commit()
    return c.id


def test_tip_flow_filter_flag_and_delete(client):
    a = register_and_login(client, email="a@example.com")[1]
    b = register_and_login(client, email="b@example.com")[1]
    cid = _mk(client)
    assert client.get(f"{API}/companies/{cid}/comments").status_code == 200  # public
    assert client.post(f"{API}/companies/{cid}/comments", json={"kind": "works"}).status_code in (401, 403)
    r = client.post(f"{API}/companies/{cid}/comments", headers=_h(a), json={"kind": "works"})
    assert r.status_code == 201
    r = client.post(f"{API}/companies/{cid}/comments", headers=_h(a), json={"kind": "tip", "body": "Apply before Friday"})
    assert r.status_code == 201
    assert client.post(f"{API}/companies/{cid}/comments", headers=_h(a), json={"kind": "tip"}).status_code == 422
    assert client.post(f"{API}/companies/{cid}/comments", headers=_h(a),
                       json={"kind": "tip", "body": "visit https://evil.example"}).status_code == 422
    data = client.get(f"{API}/companies/{cid}/comments", headers=_h(b)).json()
    assert data["counts"]["works"] == 1 and len(data["comments"]) == 2
    assert all(not c["mine"] for c in data["comments"])
    assert client.get(f"{API}/comments/summary", headers=_h(b)).json()[cid]["total"] == 2
    tip = next(c for c in data["comments"] if c["kind"] == "tip")
    assert client.post(f"{API}/comments/{tip['id']}/flag", headers=_h(b)).status_code == 204
    assert client.delete(f"{API}/comments/{tip['id']}", headers=_h(b)).status_code == 404
    assert client.delete(f"{API}/comments/{tip['id']}", headers=_h(a)).status_code == 204
