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


def test_tagging_notifies_only_opted_in_members(client):
    a = register_and_login(client, email="a@example.com")[1]
    b = register_and_login(client, email="b@example.com")[1]
    c = register_and_login(client, email="c@example.com")[1]
    cid = _mk(client)
    bid = client.get(f"{API}/auth/me", headers=_h(b)).json()["id"]
    cid_user = client.get(f"{API}/auth/me", headers=_h(c)).json()["id"]
    client.put(f"{API}/messages/settings", headers=_h(b), json={"allow_messages": True})
    ms = client.get(f"{API}/messages/members", headers=_h(a)).json()
    assert [m["id"] for m in ms] == [bid] and "position" in ms[0]
    r = client.post(f"{API}/companies/{cid}/comments", headers=_h(a),
                    json={"kind": "tip", "body": "@Th check this", "mentions": [bid, cid_user]})
    assert r.status_code == 201
    nb = client.get(f"{API}/notifications", headers=_h(b)).json()
    nc = client.get(f"{API}/notifications", headers=_h(c)).json()
    assert any(n["type"] == "mention" for n in (nb if isinstance(nb, list) else nb.get("items", [])))
    assert not any(n["type"] == "mention" for n in (nc if isinstance(nc, list) else nc.get("items", [])))


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
