"""Tests for the /watches notify-me subscription routes."""
from tests.conftest import register_and_login


def _auth_header(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_subscribe_requires_a_scope(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/watches", json={}, headers=_auth_header(tokens))
    assert r.status_code == 400


def test_subscribe_and_list_by_country(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/watches", json={"country": "Zambia", "source_type": "uni"},
                    headers=_auth_header(tokens))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["country"] == "Zambia"
    assert body["source_type"] == "UNI"  # normalised upper-case

    listed = client.get("/api/v1/watches", headers=_auth_header(tokens)).json()
    assert len(listed) == 1 and listed[0]["id"] == body["id"]


def test_unsubscribe_removes_it_from_the_list(client):
    _, tokens = register_and_login(client)
    created = client.post("/api/v1/watches", json={"country": "Kenya"}, headers=_auth_header(tokens)).json()
    r = client.delete(f"/api/v1/watches/{created['id']}", headers=_auth_header(tokens))
    assert r.status_code == 204
    listed = client.get("/api/v1/watches", headers=_auth_header(tokens)).json()
    assert listed == []


def test_watches_are_per_user(client):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    client.post("/api/v1/watches", json={"country": "Ghana"}, headers=_auth_header(tokens_a))
    listed_b = client.get("/api/v1/watches", headers=_auth_header(tokens_b)).json()
    assert listed_b == []


def test_requires_authentication(client):
    r = client.post("/api/v1/watches", json={"country": "Ghana"})
    assert r.status_code in (401, 403)
