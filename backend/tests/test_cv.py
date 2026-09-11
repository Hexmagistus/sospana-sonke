"""Tests for CV upload, validation, extraction, structuring, and apply-to-profile."""
import io

from tests.conftest import register_and_login

SAMPLE_CV = """Thandi Mokoena
Johannesburg, South Africa
thandi.mokoena@example.com | +27 82 123 4567
https://www.linkedin.com/in/thandimokoena
https://github.com/thandim

PROFILE
Operations professional with 6 years of experience in logistics and warehouse management.

EXPERIENCE
Operations Supervisor at Acme Logistics
Led a team of 12 in warehouse operations.

EDUCATION
BCom Accounting, University of the Witwatersrand

SKILLS
Python, SQL, Excel, SAP, Project Management, Communication

LANGUAGES
English, Zulu
"""


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _txt(content=SAMPLE_CV):
    return ("cv.txt", io.BytesIO(content.encode()), "text/plain")


def _docx(content=SAMPLE_CV):
    from docx import Document
    doc = Document()
    for line in content.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return ("cv.docx", buf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def _pdf(content=SAMPLE_CV):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in content.splitlines():
        c.drawString(40, y, line)
        y -= 16
    c.save()
    buf.seek(0)
    return ("cv.pdf", buf, "application/pdf")


def test_upload_txt_extracts_and_structures(client):
    _, tokens = register_and_login(client)
    r = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": _txt()})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["parse_status"] == "parsed"
    assert body["extension"] == "txt"
    assert len(body["file_hash"]) == 64

    structured = client.get(f"/api/v1/cv/{body['id']}/structured", headers=_auth(tokens)).json()["structured"]
    assert structured["email"] == "thandi.mokoena@example.com"
    assert "linkedin.com/in/thandimokoena" in (structured.get("linkedin_url") or "")
    skill_names = {s["name"].lower() for s in structured.get("skills", [])}
    assert {"python", "sql", "sap"}.issubset(skill_names)
    assert "English" in structured.get("languages", [])

    # "About you" fields — occupation from the role line, years from the explicit
    # statement, city from the header line — never computed or guessed beyond that.
    assert structured["current_occupation"] == "Operations Supervisor"
    assert structured["years_experience"] == 6
    assert structured["city"] == "Johannesburg"
    exp = structured["work_experience"][0]
    assert exp["position"] == "Operations Supervisor"
    assert exp["employer"] == "Acme Logistics"


def test_upload_docx_and_pdf(client):
    _, tokens = register_and_login(client)
    for f in (_docx(), _pdf()):
        r = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": f})
        assert r.status_code == 201, r.text
        assert r.json()["parse_status"] == "parsed"


def test_reject_unsupported_type(client):
    _, tokens = register_and_login(client)
    f = ("cv.exe", io.BytesIO(b"MZ\x90\x00binary"), "application/octet-stream")
    r = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": f})
    assert r.status_code == 400


def test_reject_fake_pdf(client):
    # A text file renamed to .pdf must be caught by the magic-byte check.
    _, tokens = register_and_login(client)
    f = ("cv.pdf", io.BytesIO(b"this is not really a pdf"), "application/pdf")
    r = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": f})
    assert r.status_code == 400
    assert "pdf" in r.json()["detail"].lower()


def test_reject_empty_file(client):
    _, tokens = register_and_login(client)
    f = ("cv.txt", io.BytesIO(b""), "text/plain")
    r = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": f})
    assert r.status_code == 400


def test_apply_to_profile_adds_unconfirmed_records(client):
    _, tokens = register_and_login(client)
    h = _auth(tokens)
    cv = client.post("/api/v1/cv", headers=h, files={"file": _txt()}).json()

    applied = client.post(f"/api/v1/cv/{cv['id']}/apply-to-profile", headers=h, json={}).json()
    assert applied["skills_added"] >= 3
    assert "linkedin_url" in applied["profile_fields_filled"]
    assert "current_occupation" in applied["profile_fields_filled"]
    assert "city" in applied["profile_fields_filled"]
    assert "years_experience" in applied["profile_fields_filled"]

    # Imported skills must be UNCONFIRMED (candidate has not verified them yet).
    skills = client.get("/api/v1/profile/skills", headers=h).json()
    assert skills and all(s["confirmed_by_candidate"] is False for s in skills)
    assert all(s["source"] == "cv_extraction" for s in skills)

    # "About you" is filled straight onto the profile (visible/editable there).
    profile = client.get("/api/v1/profile", headers=h).json()
    assert profile["current_occupation"] == "Operations Supervisor"
    assert profile["city"] == "Johannesburg"
    assert profile["years_experience"] == 6


def test_apply_to_profile_never_overwrites_existing_values(client):
    _, tokens = register_and_login(client)
    h = _auth(tokens)
    # The candidate has already set their own occupation — a CV import must not
    # clobber it, even if the CV suggests something different.
    client.put("/api/v1/profile", headers=h, json={"current_occupation": "Senior Analyst", "city": "Cape Town"})
    cv = client.post("/api/v1/cv", headers=h, files={"file": _txt()}).json()
    client.post(f"/api/v1/cv/{cv['id']}/apply-to-profile", headers=h, json={})

    profile = client.get("/api/v1/profile", headers=h).json()
    assert profile["current_occupation"] == "Senior Analyst"
    assert profile["city"] == "Cape Town"


def test_download_and_ownership(client):
    _, tokens_a = register_and_login(client, email="a@example.com")
    _, tokens_b = register_and_login(client, email="b@example.com")
    cv = client.post("/api/v1/cv", headers=_auth(tokens_a), files={"file": _txt()}).json()

    # Owner can download and gets the original bytes back.
    dl = client.get(f"/api/v1/cv/{cv['id']}/download", headers=_auth(tokens_a))
    assert dl.status_code == 200 and b"Thandi Mokoena" in dl.content

    # Another user cannot see or download it.
    assert client.get(f"/api/v1/cv/{cv['id']}", headers=_auth(tokens_b)).status_code == 404
    assert client.get(f"/api/v1/cv/{cv['id']}/download", headers=_auth(tokens_b)).status_code == 404
    assert client.get("/api/v1/cv", headers=_auth(tokens_b)).json() == []


def test_original_preserved_flag(client):
    _, tokens = register_and_login(client)
    cv = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": _txt()}).json()
    assert cv["is_original"] is True
