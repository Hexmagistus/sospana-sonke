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


def test_profile_seeded_from_registration_answers(client):
    # A candidate who wrote down a preferred role and qualification at
    # registration shouldn't have to retype them: the first-ever profile
    # fetch seeds desired_occupations and an unconfirmed Education row from
    # those answers.
    email = "seeded@example.com"
    reg = client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!",
        "first_name": "Sipho", "last_name": "Dlamini", "mobile_number": "0821234567",
        "preferred_position": "Warehouse Supervisor", "qualification_name": "National Diploma: Logistics",
    })
    assert reg.status_code == 201, reg.text
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"}).json()
    h = _auth(tokens)

    body = client.get("/api/v1/profile", headers=h).json()
    assert body["desired_occupations"] == ["Warehouse Supervisor"]

    edu = client.get("/api/v1/profile/education", headers=h).json()
    assert len(edu) == 1
    assert edu[0]["qualification"] == "National Diploma: Logistics"
    assert edu[0]["source"] == "registration"
    assert edu[0]["confirmed_by_candidate"] is False

    # It's a one-time seed, never re-applied and never overwriting a
    # candidate's own edit.
    client.put("/api/v1/profile", headers=h, json={"desired_occupations": ["Fleet Manager"]})
    body2 = client.get("/api/v1/profile", headers=h).json()
    assert body2["desired_occupations"] == ["Fleet Manager"]
    assert len(client.get("/api/v1/profile/education", headers=h).json()) == 1


def test_profile_not_seeded_without_registration_answers(client):
    # register_and_login leaves preferred_position/qualification_name blank --
    # confirms the seed is opt-in and doesn't fabricate data.
    _, tokens = register_and_login(client)
    h = _auth(tokens)
    body = client.get("/api/v1/profile", headers=h).json()
    assert body["desired_occupations"] in (None, [])
    assert client.get("/api/v1/profile/education", headers=h).json() == []


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
