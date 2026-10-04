"""Tests for document generation: builder, truthfulness, ATS, and the full route flow."""
from tests.conftest import register_and_login
from app.documents.builder import build_tailored_cv, build_summary
from app.documents.truthfulness import ProfileFacts, validate_cv
from app.documents.ats import score_ats


# ---- unit tests -------------------------------------------------------------

def test_builder_orders_relevant_skills_first():
    facts = {"skills": ["Communication", "SQL", "Excel"], "years_experience": 5,
             "current_occupation": "Analyst"}
    cv = build_tailored_cv(facts, {"title": "Data Analyst", "skill_terms": {"sql"}})
    assert cv["skills"][0] == "SQL"  # relevant skill floated to the top


def test_builder_summary_is_truthful():
    facts = {"current_occupation": "Operations Supervisor", "years_experience": 6,
             "industries": ["logistics"]}
    summary = build_summary(facts, "Operations Manager")
    assert "6 years" in summary and "logistics" in summary


def test_truthfulness_passes_for_clean_cv():
    facts = ProfileFacts(skills={"sql", "excel"}, employers={"acme"}, institutions={"wits"},
                         years_experience=6)
    cv = {"skills": ["SQL", "Excel"], "experience": [{"employer": "Acme"}],
          "education": [{"institution": "Wits"}], "summary": "Analyst with 6 years of experience."}
    result = validate_cv(cv, facts)
    assert result.ok and result.violations == []


def test_truthfulness_catches_fabrication():
    facts = ProfileFacts(skills={"sql"}, employers={"acme"}, years_experience=6)
    cv = {"skills": ["SQL", "Photoshop"],                       # Photoshop not in profile
          "experience": [{"employer": "Globex"}],               # Globex not in profile
          "summary": "Analyst with 12 years of experience."}    # inflated years
    result = validate_cv(cv, facts)
    assert result.ok is False
    joined = " ".join(result.violations)
    assert "Photoshop" in joined and "Globex" in joined and "12 years" in joined


def test_ats_scorer():
    cv = {"full_name": "T M", "email": "t@x.co", "phone": "0821234567",
          "summary": "s", "skills": ["SQL", "Excel"], "experience": [{}], "education": [{}]}
    score, breakdown = score_ats(cv, {"sql", "excel", "python"})
    assert 0 <= score <= 100
    assert breakdown["keyword_relevance"] == round(2 / 3 * 100, 1)
    assert breakdown["structure"] == 100.0
    assert breakdown["contact_info"] == 100.0


# ---- route integration ------------------------------------------------------

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
                json={"employer": "Acme Logistics", "position": "Supervisor", "is_current": True,
                      "responsibilities": "Ran the warehouse team."})


_JOB = {"job_title": "Operations Manager", "company_name": "Acme Logistics",
        "job_description": "SQL and Excel needed. Minimum of 5 years experience required."}


def test_generate_cv_and_cover_letter_for_a_named_job(client):
    """Tailored CVs keep working without matching: a role the candidate names or pastes."""
    _, tokens = register_and_login(client)
    _enrich(client, tokens)

    gen = client.post("/api/v1/tailor", headers=_auth(tokens), json=_JOB)
    assert gen.status_code == 201, gen.text
    cv, letter = gen.json()["cv_version"], gen.json()["cover_letter"]
    assert cv["truthfulness_ok"] is True
    assert cv["ats_score"] and cv["ats_score"] > 0
    assert cv["label"].endswith("_CV")
    assert "Operations Manager" in letter["body"] and "Acme Logistics" in letter["body"]
    assert letter["truthfulness_ok"] is True

    pdf = client.get(f"/api/v1/cv-versions/{cv['id']}/download", params={"fmt": "pdf"}, headers=_auth(tokens))
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    docx = client.get(f"/api/v1/cv-versions/{cv['id']}/download", params={"fmt": "docx"}, headers=_auth(tokens))
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
    lpdf = client.get(f"/api/v1/cover-letters/{letter['id']}/download", headers=_auth(tokens))
    assert lpdf.status_code == 200 and lpdf.content[:5] == b"%PDF-"

    assert len(client.get("/api/v1/cv-versions", headers=_auth(tokens)).json()) == 1
    assert len(client.get("/api/v1/cover-letters", headers=_auth(tokens)).json()) == 1


def test_generating_from_a_match_is_gone(client):
    _, tokens = register_and_login(client)
    for path in ("generate-cv", "generate-cover-letter", "interview-prep", "prepare-application"):
        r = client.post(f"/api/v1/matches/some-id/{path}", headers=_auth(tokens))
        assert r.status_code == 410, path


def test_document_ownership(client):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    _enrich(client, tokens_a)
    cv = client.post("/api/v1/tailor", headers=_auth(tokens_a), json=_JOB).json()["cv_version"]

    # B cannot see or download A's CV version.
    assert client.get(f"/api/v1/cv-versions/{cv['id']}", headers=_auth(tokens_b)).status_code == 404
    assert client.get(f"/api/v1/cv-versions/{cv['id']}/download",
                      headers=_auth(tokens_b)).status_code == 404
    assert client.get("/api/v1/cv-versions", headers=_auth(tokens_b)).json() == []
