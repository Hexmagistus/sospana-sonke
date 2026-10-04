"""Tests for application lifecycle, audit trail, answers and preferences (applications are no longer\nprepared from job matches, so they are created directly in the DB here)."""
from tests.conftest import register_and_login
from tests.helpers_apps import make_application


def _auth(t):
    return {"Authorization": f"Bearer {t['access_token']}"}


def _get(client, tokens, app_id):
    return client.get(f"/api/v1/applications/{app_id}", headers=_auth(tokens)).json()


def test_preferences_default_and_update(client):
    _, tokens = register_and_login(client)
    got = client.get("/api/v1/preferences", headers=_auth(tokens)).json()
    assert got["application_mode"] == "approval" and got["max_applications_per_day"] == 5

    upd = client.put("/api/v1/preferences", headers=_auth(tokens), json={
        "application_mode": "assisted", "auto_apply_enabled": False, "min_match_score": 75,
        "max_applications_per_day": 3, "max_applications_per_week": 10,
        "excluded_companies": [], "excluded_roles": ["cleaner"]})
    assert upd.status_code == 200 and upd.json()["application_mode"] == "assisted"


def test_prepare_from_a_match_is_gone(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/matches/anything/prepare-application", headers=_auth(tokens))
    assert r.status_code == 410


def test_existing_application_lists_with_answers_and_no_match_fields(client, db_engine):
    _, tokens = register_and_login(client)
    app_id = make_application(client, tokens, db_engine)
    app = _get(client, tokens, app_id)
    assert app["status"] == "AWAITING_APPROVAL" and app["vacancy_title"] == "Operations Manager"
    assert "match_score" not in app and "match_band" not in app
    qs = {a["question"]: a for a in app["answers"]}
    assert not qs["How many years of relevant experience do you have?"]["is_unknown"]
    assert qs["What is your notice period?"]["is_unknown"] is True
    listed = client.get("/api/v1/applications", headers=_auth(tokens)).json()
    assert [a["id"] for a in listed] == [app_id] and "match_score" not in listed[0]


def test_full_lifecycle_with_audit_trail(client, db_engine):
    _, tokens = register_and_login(client)
    app_id = make_application(client, tokens, db_engine)

    approved = client.post(f"/api/v1/applications/{app_id}/approve", headers=_auth(tokens)).json()
    assert approved["status"] == "CANDIDATE_ACTION_REQUIRED" and approved["authorised_at"]

    submitted = client.post(f"/api/v1/applications/{app_id}/mark-submitted", headers=_auth(tokens)).json()
    assert submitted["status"] == "SUBMITTED" and submitted["submitted_at"]

    interview = client.post(f"/api/v1/applications/{app_id}/status", headers=_auth(tokens),
                            json={"status": "interview"}).json()
    assert interview["status"] == "INTERVIEW"

    types = [e["event_type"] for e in _get(client, tokens, app_id)["events"]]
    assert "prepared" in types and "approved" in types and "submitted" in types and "status_update" in types


def test_fill_unknown_answer(client, db_engine):
    _, tokens = register_and_login(client)
    app = _get(client, tokens, make_application(client, tokens, db_engine))
    notice = next(a for a in app["answers"] if a["question"] == "What is your notice period?")
    filled = client.put(f"/api/v1/applications/{app['id']}/answers/{notice['id']}",
                        headers=_auth(tokens), json={"value": "30 days"}).json()
    assert filled["answer"] == "30 days" and filled["source"] == "candidate" and filled["is_unknown"] is False


def test_invalid_status_rejected(client, db_engine):
    _, tokens = register_and_login(client)
    app_id = make_application(client, tokens, db_engine)
    r = client.post(f"/api/v1/applications/{app_id}/status", headers=_auth(tokens),
                    json={"status": "SUBMITTED"})  # not a candidate-settable status
    assert r.status_code == 400


def test_application_ownership(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    app_id = make_application(client, tokens_a, db_engine)
    assert client.get(f"/api/v1/applications/{app_id}", headers=_auth(tokens_b)).status_code == 404
    assert client.get("/api/v1/applications", headers=_auth(tokens_b)).json() == []
