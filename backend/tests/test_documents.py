"""Tests for document generation: builder, truthfulness, ATS, and the full route flow."""
from datetime import datetime, timezone

from tests.conftest import register_and_login
from app.documents.builder import build_tailored_cv, build_summary
from app.documents.truthfulness import ProfileFacts, validate_cv
from app.documents.ats import score_ats
from app.models.company import Company
from app.models.vacancy import Vacancy, VacancyRequirement


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


def _seed_vacancy(db_engine):
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=db_engine)
    s = S()
    try:
        c = Company(company_name="Acme Logistics", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title="Operations Manager",
                    location="Johannesburg", description="SQL and Excel needed.",
                    content_hash="h1", is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        s.add(VacancyRequirement(vacancy_id=v.id, text="Minimum of 5 years experience required",
                                 kind="hard", category="experience"))
        s.commit()
        return v.id
    finally:
        s.close()


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


def _make_match(client, tokens, db_engine):
    _enrich(client, tokens)
    _seed_vacancy(db_engine)
    client.post("/api/v1/matches/run", headers=_auth(tokens))
    return client.get("/api/v1/matches", headers=_auth(tokens)).json()[0]["id"]


def test_generate_cv_flow(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)

    gen = client.post(f"/api/v1/matches/{match_id}/generate-cv", headers=_auth(tokens))
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["truthfulness_ok"] is True
    assert body["ats_score"] and body["ats_score"] > 0
    assert body["label"].endswith("_CV")

    pdf = client.get(f"/api/v1/cv-versions/{body['id']}/download", params={"fmt": "pdf"},
                     headers=_auth(tokens))
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    docx = client.get(f"/api/v1/cv-versions/{body['id']}/download", params={"fmt": "docx"},
                      headers=_auth(tokens))
    assert docx.status_code == 200 and docx.content[:2] == b"PK"

    listed = client.get("/api/v1/cv-versions", headers=_auth(tokens)).json()
    assert len(listed) == 1


def test_generate_cover_letter_flow(client, db_engine):
    _, tokens = register_and_login(client)
    match_id = _make_match(client, tokens, db_engine)

    gen = client.post(f"/api/v1/matches/{match_id}/generate-cover-letter", headers=_auth(tokens))
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert "Operations Manager" in body["body"]
    assert "Acme Logistics" in body["body"]
    assert body["truthfulness_ok"] is True

    pdf = client.get(f"/api/v1/cover-letters/{body['id']}/download", headers=_auth(tokens))
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"


def test_document_ownership(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    match_id = _make_match(client, tokens_a, db_engine)
    cv = client.post(f"/api/v1/matches/{match_id}/generate-cv", headers=_auth(tokens_a)).json()

    # B cannot see or download A's CV version.
    assert client.get(f"/api/v1/cv-versions/{cv['id']}", headers=_auth(tokens_b)).status_code == 404
    assert client.get(f"/api/v1/cv-versions/{cv['id']}/download",
                      headers=_auth(tokens_b)).status_code == 404
    assert client.get("/api/v1/cv-versions", headers=_auth(tokens_b)).json() == []


def test_cannot_generate_for_other_users_match(client, db_engine):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    match_id = _make_match(client, tokens_a, db_engine)
    # B tries to generate a CV from A's match.
    r = client.post(f"/api/v1/matches/{match_id}/generate-cv", headers=_auth(tokens_b))
    assert r.status_code == 404
