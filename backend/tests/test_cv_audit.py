"""Tests for the ATS CV Audit & Rebuild ("CV Doctor") pipeline."""
import io
import os
import re

from tests.conftest import register_and_login

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_cv_operations.txt")
SOURCE = open(FIXTURE, encoding="utf8").read()


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _messy_docx(text: str = SOURCE) -> tuple:
    """A deliberately ATS-unfriendly Word CV: contact details in the page
    header and the skills laid out in a table."""
    from docx import Document
    doc = Document()
    doc.sections[0].header.paragraphs[0].text = "sipho.nkosi@example.com | 082 555 0199"
    for line in text.splitlines():
        if line.startswith("Process monitoring"):
            t = doc.add_table(rows=1, cols=3)
            for i, cell in enumerate(line.split(",")[:3]):
                t.rows[0].cells[i].text = cell
            continue
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return ("Sipho CV.docx", buf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# ---- Unit: parser ------------------------------------------------------------------

def test_parser_extracts_roles_dates_and_statuses():
    from app.documents.cv_audit.parse import parse_cv_text
    cv = parse_cv_text(SOURCE)
    assert cv["full_name"] == "Sipho James Nkosi"
    assert cv["email"] == "sipho.nkosi@example.com"
    roles = [(e["position"], e["employer"], e["start"], e["end"]) for e in cv["experience"]]
    assert roles == [
        ("Process Controller Assistant", "Rand Water", "Mar 2022", "Present"),
        ("Rolls Plant Process Controller", "Barloworld Ingrain SA", "Jan 2019", "Feb 2022"),
        ("Microbiology Laboratory Technician", "Tongaat Hulett Starch", "Jun 2016", "Dec 2018"),
    ]
    status = {e["qualification"]: e["status"] for e in cv["education"]}
    assert status["Postgraduate Diploma in Operations Management"] == "awaiting_conferral"
    assert status["National Diploma: Biotechnology"] == "completed"
    certs = {c["name"]: c for c in cv["certifications"]}
    assert certs["Water and Wastewater Process Control NQF 4"]["status"] == "in_progress"
    assert certs["National Certificate: Chemical Operations"]["issuer"] == "CHIETA"
    kinds = {s["kind"] for s in cv["sensitive"]}
    assert {"id_number", "date_of_birth", "gender", "marital_status"} <= kinds
    assert cv["references_present"] is True


def test_parser_repairs_pdf_bullet_artefacts():
    from app.documents.cv_audit.parse import parse_cv_text
    text = ("Jane Dube\njane@example.com\nWORK EXPERIENCE\nLab Analyst\nAcme Foods (Pty) Ltd | Jan 2020 – Present\n"
            "\x7f\n\nTested raw materials against the product\nspecification every shift\n Calibrated balances\n")
    exp = parse_cv_text(text)["experience"]
    assert len(exp) == 1
    assert exp[0]["bullets"] == ["Tested raw materials against the product specification every shift",
                                 "Calibrated balances"]


# ---- Unit: rewrite truthfulness ----------------------------------------------------------

def test_rebuild_never_invents_numbers_or_upgrades_verbs():
    from app.documents.cv_audit.parse import parse_cv_text
    from app.documents.cv_audit.rewrite import build_rebuilt_cv
    cv, _ = build_rebuilt_cv(parse_cv_text(SOURCE), SOURCE)
    source_numbers = set(re.findall(r"\d+", SOURCE))
    produced = " ".join([cv["summary"], cv["headline"]] + [b for e in cv["experience"] for b in e["bullets"]])
    assert set(re.findall(r"\d+", produced)) <= source_numbers
    bullets = [b for e in cv["experience"] for b in e["bullets"]]
    # "Assisted with…" / "Helped with…" stay assistance — never become "Led"/"Managed".
    assert "Assist with chemical dosing adjustments under supervision" in bullets
    assert "Assisted with training of 3 new operators" in bullets
    assert not any(b.split()[0] in ("Led", "Managed", "Supervised", "Spearheaded") for b in bullets)
    # Current role in present tense, past roles in past tense.
    assert cv["experience"][0]["bullets"][0] == "Monitor sedimentation tanks and filters"
    assert "Conducted microbiological testing of raw materials and products" in cv["experience"][2]["bullets"]
    # Titles, employers and qualification names are untouched.
    assert [e["position"] for e in cv["experience"]][1] == "Rolls Plant Process Controller"
    assert cv["current_studies"][0]["qualification"] == "Postgraduate Diploma in Operations Management"
    # Sensitive data never reaches the rebuilt CV.
    blob = repr(cv)
    assert "9001015009087" not in blob and "Married" not in blob and "Mokoena" not in blob
    # Acronyms spelt out once, in reading order (competencies come before experience).
    comps = [t for ts in cv["competencies"].values() for t in ts]
    assert "Supervisory Control and Data Acquisition (SCADA)" in comps
    assert any("SCADA" in b and "Supervisory" not in b for b in bullets)


def test_competencies_are_all_evidenced():
    from app.documents.cv_audit.parse import parse_cv_text
    from app.documents.cv_audit.rewrite import build_rebuilt_cv
    cv, _ = build_rebuilt_cv(parse_cv_text(SOURCE), SOURCE)
    low = SOURCE.lower()
    for term in [t for ts in cv["competencies"].values() for t in ts]:
        core = term.split(" (")[-1].rstrip(")") if "(" in term else term
        words = [w for w in re.findall(r"[a-z]{4,}", core.lower())]
        assert any(w[:5] in low for w in words) or core.lower() in low, term


# ---- End to end ---------------------------------------------------------------------------

def _upload_and_audit(client, tokens):
    up = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": _messy_docx()})
    assert up.status_code == 201, up.text
    resp = client.post("/api/v1/cv-audits", headers=_auth(tokens), json={"cv_id": up.json()["id"]})
    assert resp.status_code == 201, resp.text
    return up.json(), resp.json()


def test_full_audit_flow(client):
    _, tokens = register_and_login(client)
    cv, audit = _upload_and_audit(client, tokens)

    codes = {f["code"] for f in audit["findings"]}
    assert {"tables", "contact_in_header"} <= codes
    before, after = audit["original_scores"], audit["final_scores"]
    assert after["areas"]["ats_compatibility"]["score"] > before["areas"]["ats_compatibility"]["score"]
    assert after["overall"] > before["overall"]
    assert "not an official rating" in after["disclaimer"]
    assert audit["stress"]["passed"] == audit["stress"]["total"], audit["stress"]["checks"]
    assert audit["pages"] <= 2
    assert any(i["category"] == "Achievements" for i in audit["checklist"])
    assert 1 <= len(audit["directions"]) <= 3

    from pypdf import PdfReader
    from docx import Document
    for kind, check in (("pdf", None), ("docx", None), ("report", None)):
        r = client.get(f"/api/v1/cv-audits/{audit['id']}/file/{kind}", headers=_auth(tokens))
        assert r.status_code == 200, (kind, r.text)
        assert "attachment" in r.headers["content-disposition"]
        if kind == "docx":
            d = Document(io.BytesIO(r.content))
            assert not d.tables
            assert not "".join(p.text for p in d.sections[0].header.paragraphs).strip()
            assert d.paragraphs[0].text == "Sipho James Nkosi"
        else:
            text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
            assert ("Sipho James Nkosi" in text) if kind == "pdf" else ("ATS CV Audit Report" in text)

    # Candidate adds a verified figure and confirms a role; everything re-scores.
    rebuilt = audit["rebuilt"]
    rebuilt["experience"][0]["bullets"].append("Monitor 12 sedimentation tanks per shift")
    r = client.put(f"/api/v1/cv-audits/{audit['id']}/cv", headers=_auth(tokens), json=rebuilt)
    assert r.status_code == 200, r.text
    edited = r.json()
    assert edited["edited_by_candidate"] is True
    assert "Monitor 12 sedimentation tanks per shift" in edited["rebuilt"]["experience"][0]["bullets"]
    assert edited["final_scores"]["areas"]["recruitment_effectiveness"]["score"] >= \
        after["areas"]["recruitment_effectiveness"]["score"]

    lst = client.get("/api/v1/cv-audits", headers=_auth(tokens)).json()
    assert [a["id"] for a in lst] == [audit["id"]]


def test_audit_is_private_and_deleted_with_cv(client):
    _, owner = register_and_login(client)
    cv, audit = _upload_and_audit(client, owner)
    _, other = register_and_login(client, email="other@example.com")
    for path in (f"/api/v1/cv-audits/{audit['id']}", f"/api/v1/cv-audits/{audit['id']}/file/pdf"):
        assert client.get(path, headers=_auth(other)).status_code == 404
    assert client.post("/api/v1/cv-audits", headers=_auth(other), json={"cv_id": cv["id"]}).status_code == 404
    assert client.delete(f"/api/v1/cv/{cv['id']}", headers=_auth(owner)).status_code == 204
    assert client.get(f"/api/v1/cv-audits/{audit['id']}", headers=_auth(owner)).status_code == 404


def test_edit_payload_is_capped(client):
    _, tokens = register_and_login(client)
    _, audit = _upload_and_audit(client, tokens)
    bad = audit["rebuilt"]
    bad["summary"] = "x" * 10000
    r = client.put(f"/api/v1/cv-audits/{audit['id']}/cv", headers=_auth(tokens), json=bad)
    assert r.status_code == 422


def test_unreadable_cv_is_refused(client):
    _, tokens = register_and_login(client)
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.rect(50, 50, 200, 200, fill=1)  # an "image-only" page with no text
    c.save()
    buf.seek(0)
    up = client.post("/api/v1/cv", headers=_auth(tokens), files={"file": ("scan.pdf", buf, "application/pdf")})
    assert up.status_code == 201
    r = client.post("/api/v1/cv-audits", headers=_auth(tokens), json={"cv_id": up.json()["id"]})
    assert r.status_code == 409
