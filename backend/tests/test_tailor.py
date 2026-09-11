"""Tests for the "Tailor my CV to a job" pipeline (job analysis, match report,
fact-check, CV/cover-letter/interview-prep generation, application tracker) —
routes_tailor.py + job_analysis_service.py."""
from tests.conftest import register_and_login

JOB_AD = """
Senior Operations Manager - Acme Logistics

We are looking for a Senior Operations Manager to lead our Johannesburg
distribution centre.

Requirements:
- Minimum of 5 years experience in operations or logistics management
- Bachelor's degree in Business, Logistics or related field required
- Strong proficiency in SQL and Excel
- Experience with warehouse management systems preferred
- Excellent communication and leadership skills
- A valid driver's licence is required
- Professional certification in supply chain management is an advantage

Key Responsibilities:
- Manage the daily production schedule and warehouse team
- Oversee inventory control and reporting
- Coordinate with suppliers and logistics partners
- Drive continuous improvement initiatives across the site

We are a logistics company operating across Southern Africa.
"""


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _enrich(client, tokens):
    h = _auth(tokens)
    client.put("/api/v1/profile", headers=h, json={
        "years_experience": 6, "current_occupation": "Operations Supervisor",
        "desired_occupations": ["Operations Manager"], "industries": ["logistics"],
        "preferred_locations": ["Johannesburg"],
    })
    client.post("/api/v1/profile/skills", headers=h, json={"name": "SQL", "category": "technical"})
    client.post("/api/v1/profile/skills", headers=h, json={"name": "Excel", "category": "software"})
    client.post("/api/v1/profile/education", headers=h,
                json={"institution": "Wits", "qualification": "BCom", "level": "Degree"})
    client.post("/api/v1/profile/experience", headers=h,
                json={"employer": "Acme Logistics", "position": "Operations Supervisor",
                      "is_current": True,
                      "responsibilities": "Managed the daily production schedule and warehouse team, "
                                          "oversaw inventory control and reporting.",
                      "achievements": "Reduced order-processing errors."})


def test_master_cv_endpoint_reflects_profile(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    resp = client.get("/api/v1/profile/master-cv", headers=_auth(tokens))
    assert resp.status_code == 200, resp.text
    facts = resp.json()
    assert "SQL" in facts["skills"]
    assert facts["current_occupation"] == "Operations Supervisor"


def test_templates_listed():
    from app.documents.render import list_templates
    templates = list_templates()
    ids = {t["id"] for t in templates}
    assert {"executive", "professional", "modern", "ats_pro", "academic"} <= ids


def test_analyze_job_never_fabricates_and_scores(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    h = _auth(tokens)

    resp = client.post("/api/v1/tailor/analyze", headers=h, json={
        "job_title": None, "company_name": "Acme Logistics", "job_description": JOB_AD,
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    analysis = body["job_analysis"]

    # Title was inferred, not left blank or fabricated from nothing.
    assert "Operations Manager" in analysis["job_title"]

    # Sub-scores present and in range, formula-based (not random — re-running
    # analyze on the same input must reproduce the same score).
    for key in ("qualification", "experience", "technical_skill", "industry",
               "certification", "keyword", "responsibility"):
        assert key in analysis["sub_scores"]
        assert 0 <= analysis["sub_scores"][key] <= 100
    assert 0 <= analysis["match_score"] <= 100

    # Strong matches reflect real profile content (SQL/Excel present in CV).
    strong_texts = " ".join(m["text"] for m in analysis["strong_matches"]).lower()
    assert "sql" in strong_texts or "excel" in strong_texts

    # Missing requirements are phrased as "not found", never "you don't have this".
    all_notes = " ".join(m["note"] for m in
                         [*analysis["partial_matches"], *analysis["missing_requirements"]])
    assert "you don't have" not in all_notes.lower()
    if analysis["missing_requirements"]:
        assert "not found in your cv" in all_notes.lower()

    # ATS + quality scores computed, not stubbed to zero.
    assert analysis["ats_score"] is not None
    assert analysis["quality_score"] is not None
    assert analysis["readiness_score"] is not None
    assert analysis["readiness_label"]

    # Draft CV never invents an employer/skill absent from the real profile.
    fact_check = body["fact_check"]
    draft_cv = body["draft_cv"]
    assert isinstance(draft_cv["skills"], list)
    for exp in draft_cv.get("experience", []):
        assert exp.get("employer") in (None, "Acme Logistics")
    assert fact_check["ok"] is True
    assert fact_check["violations"] == []


def _analyze(client, h):
    resp = client.post("/api/v1/tailor/analyze", headers=h, json={
        "company_name": "Acme Logistics", "job_description": JOB_AD,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_deterministic_scoring_is_reproducible(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    h = _auth(tokens)
    a1 = _analyze(client, h)["job_analysis"]
    a2 = _analyze(client, h)["job_analysis"]
    assert a1["match_score"] == a2["match_score"]
    assert a1["sub_scores"] == a2["sub_scores"]


def test_generate_cv_cover_letter_and_interview_prep(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    h = _auth(tokens)

    result = _analyze(client, h)
    job_analysis_id = result["job_analysis"]["id"]
    draft_cv = result["draft_cv"]

    cv_resp = client.post(f"/api/v1/tailor/{job_analysis_id}/generate-cv", headers=h,
                          json={"cv_data": draft_cv, "template": "modern"})
    assert cv_resp.status_code == 201, cv_resp.text
    cv_body = cv_resp.json()
    assert cv_body["truthfulness_ok"] is True
    assert cv_body["ats_score"] and cv_body["ats_score"] > 0

    pdf = client.get(f"/api/v1/cv-versions/{cv_body['id']}/download", params={"fmt": "pdf"},
                     headers=h)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    docx = client.get(f"/api/v1/cv-versions/{cv_body['id']}/download", params={"fmt": "docx"},
                      headers=h)
    assert docx.status_code == 200
    assert docx.content[:2] == b"PK"

    letter_resp = client.post(f"/api/v1/tailor/{job_analysis_id}/generate-cover-letter", headers=h)
    assert letter_resp.status_code == 201, letter_resp.text
    assert "Acme Logistics" in letter_resp.json()["body"]

    prep_resp = client.post(f"/api/v1/tailor/{job_analysis_id}/interview-prep", headers=h)
    assert prep_resp.status_code == 201, prep_resp.text
    prep = prep_resp.json()
    assert prep["content"]["questions"]

    prep_get = client.get(f"/api/v1/tailor/{job_analysis_id}/interview-prep", headers=h)
    assert prep_get.status_code == 200

    # The application-tracker row was updated with the generated document ids.
    application = client.get(f"/api/v1/tailor/applications/{job_analysis_id}", headers=h).json()
    assert application["cv_version_id"] == cv_body["id"]
    assert application["cover_letter_id"] == letter_resp.json()["id"]


def test_application_tracker_crud(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    h = _auth(tokens)

    result = _analyze(client, h)
    job_analysis_id = result["job_analysis"]["id"]

    listing = client.get("/api/v1/tailor/applications", headers=h)
    assert listing.status_code == 200
    assert any(a["id"] == job_analysis_id for a in listing.json())

    update = client.put(f"/api/v1/tailor/applications/{job_analysis_id}", headers=h,
                        json={"status": "applied", "notes": "Applied via company site."})
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["status"] == "APPLIED"
    assert body["date_applied"] is not None
    assert body["notes"] == "Applied via company site."

    bad = client.put(f"/api/v1/tailor/applications/{job_analysis_id}", headers=h,
                     json={"status": "not-a-status"})
    assert bad.status_code == 400

    delete = client.delete(f"/api/v1/tailor/applications/{job_analysis_id}", headers=h)
    assert delete.status_code == 204
    gone = client.get(f"/api/v1/tailor/applications/{job_analysis_id}", headers=h)
    assert gone.status_code == 404


def test_cannot_access_another_users_job_analysis(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _enrich(client, tokens_a)
    result = _analyze(client, _auth(tokens_a))
    job_analysis_id = result["job_analysis"]["id"]

    _, tokens_b = register_and_login(client, email="b@example.com")
    resp = client.get(f"/api/v1/tailor/applications/{job_analysis_id}", headers=_auth(tokens_b))
    assert resp.status_code == 404


def test_analyze_requires_job_description(client, db_engine):
    _, tokens = register_and_login(client)
    _enrich(client, tokens)
    resp = client.post("/api/v1/tailor/analyze", headers=_auth(tokens),
                       json={"job_description": "   "})
    assert resp.status_code == 400
