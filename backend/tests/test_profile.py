"""Tests for candidate profile CRUD and ownership isolation."""
from tests.conftest import register_and_login


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_get_creates_empty_profile(client):
    _, tokens = register_and_login(client)
    r = client.get("/api/v1/profile", headers=_auth(tokens))
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] and body["city"] is None


def test_update_profile(client):
    _, tokens = register_and_login(client)
    r = client.put("/api/v1/profile", headers=_auth(tokens), json={
        "city": "Johannesburg", "country": "South Africa", "years_experience": 6,
        "desired_occupations": ["Operations Manager", "Production Manager"],
        "work_mode_preference": "hybrid", "minimum_salary": 45000, "willing_to_relocate": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["city"] == "Johannesburg"
    assert body["desired_occupations"] == ["Operations Manager", "Production Manager"]
    assert body["years_experience"] == 6


def test_invalid_enum_rejected(client):
    _, tokens = register_and_login(client)
    r = client.put("/api/v1/profile", headers=_auth(tokens), json={"work_mode_preference": "space"})
    assert r.status_code == 422


def test_child_crud_education(client):
    _, tokens = register_and_login(client)
    h = _auth(tokens)
    created = client.post("/api/v1/profile/education", headers=h, json={
        "institution": "University of the Witwatersrand", "qualification": "BCom",
        "field_of_study": "Accounting", "level": "Degree",
    })
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["confirmed_by_candidate"] is True and item["source"] == "manual"

    listed = client.get("/api/v1/profile/education", headers=h).json()
    assert len(listed) == 1

    upd = client.put(f"/api/v1/profile/education/{item['id']}", headers=h, json={
        "institution": "Wits University", "qualification": "BCom Honours",
        "field_of_study": "Accounting", "level": "Honours",
    })
    assert upd.status_code == 200 and upd.json()["qualification"] == "BCom Honours"

    dele = client.delete(f"/api/v1/profile/education/{item['id']}", headers=h)
    assert dele.status_code == 204
    assert client.get("/api/v1/profile/education", headers=h).json() == []


def test_skill_and_experience_crud(client):
    _, tokens = register_and_login(client)
    h = _auth(tokens)
    s = client.post("/api/v1/profile/skills", headers=h, json={"name": "Python", "category": "technical"})
    assert s.status_code == 201
    e = client.post("/api/v1/profile/experience", headers=h, json={
        "employer": "Acme Logistics", "position": "Operations Supervisor", "is_current": True,
    })
    assert e.status_code == 201 and e.json()["employer"] == "Acme Logistics"


def test_ownership_isolation(client):
    # User A creates a skill; User B must not see or delete it.
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    a = client.post("/api/v1/profile/skills", headers=_auth(tokens_a),
                    json={"name": "SAP", "category": "software"}).json()

    b_list = client.get("/api/v1/profile/skills", headers=_auth(tokens_b)).json()
    assert b_list == []  # B sees nothing of A's

    b_delete = client.delete(f"/api/v1/profile/skills/{a['id']}", headers=_auth(tokens_b))
    assert b_delete.status_code == 404  # B cannot touch A's record

    a_list = client.get("/api/v1/profile/skills", headers=_auth(tokens_a)).json()
    assert len(a_list) == 1  # A's data is intact
