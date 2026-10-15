"""Orchestrates the ATS CV Audit pipeline (see app/documents/cv_audit/__init__.py)."""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.documents.cv_audit.directions import build_checklist, career_directions
from app.documents.cv_audit.inspect import inspect_document
from app.documents.cv_audit.parse import parse_cv_text
from app.documents.cv_audit.render import render_docx, render_pdf
from app.documents.cv_audit.report import limitations, main_weaknesses, render_report_pdf
from app.documents.cv_audit.rewrite import build_rebuilt_cv
from app.documents.cv_audit.scoring import score_view, view_from_parsed, view_from_rebuilt
from app.documents.cv_audit.stress import stress_test
from app.models.cv import CV
from app.models.cv_audit import CVAudit
from app.models.user import User
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

MAX_AUDITS_PER_CV = 10


def _owned_cv(db: Session, user: User, cv_id: str) -> CV:
    cv = db.get(CV, cv_id)
    if cv is None or cv.user_id != user.id or cv.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
    return cv


def get_owned_audit(db: Session, user: User, audit_id: str) -> CVAudit:
    a = db.get(CVAudit, audit_id)
    if a is None or a.user_id != user.id or a.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
    return a


def _finalise(audit: CVAudit) -> None:
    """Phases 5-7: stress-test the rebuilt CV, score it, build the checklist,
    limitations and directions. Runs after the first build and after every edit."""
    rebuilt = audit.rebuilt
    stress = stress_test(rebuilt)
    pdf_text = stress.pop("pdf_text", "")
    final = score_view(view_from_rebuilt(rebuilt, pdf_text, stress["findings"], audit.parsed))
    checklist = build_checklist(audit.parsed, rebuilt)
    audit.stress = stress
    audit.pages = stress["pages"]
    audit.compact = stress["compact"]
    audit.final_scores = final
    audit.checklist = checklist
    audit.limitations = limitations(rebuilt, stress, checklist)
    audit.directions = career_directions({
        "summary": rebuilt.get("summary"),
        "skills": [t for ts in (rebuilt.get("competencies") or {}).values() for t in ts],
        "experience": rebuilt.get("experience", []),
        "education": rebuilt.get("education", []) + rebuilt.get("current_studies", []),
        "certifications": rebuilt.get("certifications", []),
    })


def run_audit(db: Session, user: User, cv_id: str) -> CVAudit:
    cv = _owned_cv(db, user, cv_id)
    if not cv.extracted_text or cv.parse_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=cv.parse_error or "No readable text was found in this CV. If it is a scanned image, upload "
                                     "a Word (DOCX) or text-based PDF version instead.")
    existing = db.query(CVAudit).filter(CVAudit.cv_id == cv.id, CVAudit.deleted_at.is_(None)).count()
    if existing >= MAX_AUDITS_PER_CV:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="This CV already has the maximum number of audits. Delete an old one first.")
    try:
        data = get_storage().get(cv.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="The original file is no longer stored. Please upload your CV again.")

    text = cv.extracted_text
    facts, findings = inspect_document(data, cv.extension, text)
    parsed = parse_cv_text(text)
    original = score_view(view_from_parsed(parsed, text, findings))
    rebuilt, change_log = build_rebuilt_cv(parsed, text)
    # Normalise through the same schema the edit endpoint uses so the stored
    # shape never differs between a fresh audit and an edited one.
    from app.schemas.cv_audit import RebuiltCV
    rebuilt = RebuiltCV.model_validate(_fit(rebuilt)).model_dump()

    audit = CVAudit(
        user_id=user.id, cv_id=cv.id, source_filename=cv.original_filename,
        document_facts=facts, findings=findings, parsed=parsed, original_scores=original,
        weaknesses=main_weaknesses(findings, original), rebuilt=rebuilt, change_log=change_log,
    )
    _finalise(audit)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def _fit(rebuilt: dict) -> dict:
    """Trim parser output to the schema caps (a very long original CV must not
    fail validation — it is truncated, and the report says the CV is long)."""
    out = dict(rebuilt)
    caps = {"experience": 20, "education": 15, "current_studies": 10, "certifications": 25, "short_courses": 25,
            "in_progress_certs": 10, "registrations": 10, "projects": 10, "achievements": 10, "languages": 12,
            "software": 30, "links": 3}
    for k, n in caps.items():
        out[k] = list(out.get(k) or [])[:n]
    for e in out["experience"]:
        e["bullets"] = [b[:2500] for b in (e.get("bullets") or [])][:25]
        for f in ("position", "employer", "location"):
            if e.get(f):
                e[f] = e[f][:300]
    for sec in ("education", "current_studies"):
        for e in out[sec]:
            if e.get("year") and not 1940 <= int(e["year"]) <= 2100:
                e["year"] = None
            for f in ("qualification", "institution"):
                if e.get(f):
                    e[f] = e[f][:300]
    if out.get("summary"):
        out["summary"] = out["summary"][:2500]
    if out.get("headline"):
        out["headline"] = out["headline"][:200]
    return out


def update_rebuilt(db: Session, user: User, audit_id: str, rebuilt: dict) -> CVAudit:
    """The candidate edits their rebuilt CV (fixing a title, adding a verified
    figure, confirming a date). They are the author, so their text is taken as
    given; everything downstream (stress test, scores, checklist) re-runs."""
    audit = get_owned_audit(db, user, audit_id)
    comp = {str(k)[:80]: [str(t)[:120] for t in (v or [])][:15]
            for k, v in list((rebuilt.get("competencies") or {}).items())[:12]}
    rebuilt["competencies"] = comp
    rebuilt["experience"] = [{**e, "bullets": [b.strip() for b in e.get("bullets", []) if b and b.strip()]}
                             for e in rebuilt.get("experience", [])]
    audit.rebuilt = rebuilt
    audit.edited_by_candidate = True
    _finalise(audit)
    db.commit()
    db.refresh(audit)
    return audit


def list_audits(db: Session, user: User) -> list[CVAudit]:
    return (db.query(CVAudit).filter(CVAudit.user_id == user.id, CVAudit.deleted_at.is_(None))
            .order_by(CVAudit.created_at.desc()).all())


def delete_audit(db: Session, user: User, audit_id: str) -> None:
    audit = get_owned_audit(db, user, audit_id)
    db.delete(audit)  # holds a copy of CV content: hard-delete (POPIA data minimisation)
    db.commit()


def file_bytes(audit: CVAudit, kind: str) -> tuple[bytes, str, str]:
    name = (audit.rebuilt.get("full_name") or "CV").strip().replace(" ", "_")
    safe = "".join(ch for ch in name if ch.isalnum() or ch in "_-")[:60] or "CV"
    if kind == "docx":
        return (render_docx(audit.rebuilt, compact=audit.compact),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{safe}_CV.docx")
    if kind == "pdf":
        return render_pdf(audit.rebuilt, compact=audit.compact), "application/pdf", f"{safe}_CV.pdf"
    if kind == "report":
        payload = {
            "candidate_name": audit.rebuilt.get("full_name"), "source_filename": audit.source_filename,
            "original_scores": audit.original_scores, "final_scores": audit.final_scores,
            "weaknesses": audit.weaknesses, "change_log": audit.change_log, "stress": audit.stress,
            "limitations": audit.limitations, "checklist": audit.checklist, "directions": audit.directions,
        }
        return render_report_pdf(payload), "application/pdf", f"{safe}_ATS_Audit_Report.pdf"
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown file.")
