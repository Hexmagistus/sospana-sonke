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


# ---- Apply the rebuilt CV to the candidate's profile ("Master CV") ------------------

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _to_date(value: str | None):
    """'Mar 2022' -> 2022-03-01, '2019' -> 2019-01-01, 'Present'/junk -> None."""
    import re
    from datetime import date
    if not value:
        return None
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+((?:19|20)\d{2})", value)
    if m and m.group(1).lower() in _MONTHS:
        return date(int(m.group(2)), _MONTHS[m.group(1).lower()], 1)
    m = re.search(r"(19|20)\d{2}", value)
    return date(int(m.group(0)), 1, 1) if m else None


def _key(*parts) -> str:
    import re
    return "|".join(re.sub(r"[^a-z0-9]", "", (p or "").lower()) for p in parts)


_STATUS_SUFFIX = {"in_progress": " (in progress)", "awaiting_conferral": " (completed – awaiting conferral)",
                  "unverified": " (status to be confirmed)"}

_SKILL_CATEGORY = {
    "Teamwork, Communication and Leadership": "soft",
    "Operations Management and Continuous Improvement": "management",
}


def apply_audit_to_profile(db: Session, user: User, audit_id: str, opts: dict) -> dict:
    """Copy the (possibly candidate-edited) rebuilt CV into the profile.

    Same contract as the CV-upload importer: we only ADD. Every new record is
    unconfirmed (shown as "from CV" until the candidate verifies it); scalar
    profile fields are filled only when empty; a record that already exists is
    never duplicated, and a confirmed record is never changed. Qualifications that
    are not completed keep their status in the title so the Master CV can never
    present them as awarded.
    """
    from app.models.profile import Certification, Education, Skill, WorkExperience
    from app.services.profile_service import get_or_create_profile

    audit = get_owned_audit(db, user, audit_id)
    cv = audit.rebuilt or {}
    profile = get_or_create_profile(db, user)
    out = {"skills": 0, "work_experience": 0, "work_experience_updated": 0, "education": 0,
           "certifications": 0, "profile_fields": [], "skipped_duplicates": 0}

    if opts.get("contact", True):
        exp = cv.get("experience") or []
        current = next((e for e in exp if e.get("is_current")), None)
        values = {
            "current_occupation": (current or {}).get("position"),
            "city": (cv.get("location") or "").split(",")[0].strip() or None,
            "linkedin_url": cv.get("linkedin_url"),
            "drivers_licence": cv.get("drivers_licence"),
        }
        limits = {"current_occupation": 160, "city": 120, "drivers_licence": 40}
        for field, val in values.items():
            if val and getattr(profile, field) in (None, ""):
                setattr(profile, field, val[:limits[field]] if field in limits else val)
                out["profile_fields"].append(field)
        if cv.get("languages") and not profile.languages:
            profile.languages = list(cv["languages"])
            out["profile_fields"].append("languages")
        mems = [r.get("name") for r in cv.get("registrations") or [] if r.get("name")]
        if mems:
            have = {m.lower() for m in (profile.professional_memberships or [])}
            new = [m for m in mems if m.lower() not in have]
            if new:
                profile.professional_memberships = list(profile.professional_memberships or []) + new
                out["profile_fields"].append("professional_memberships")

    if opts.get("skills", True):
        existing = {s.name.lower() for s in profile.skills}
        terms = [(t, _SKILL_CATEGORY.get(g, "technical")) for g, ts in (cv.get("competencies") or {}).items()
                 for t in ts] + [(t, "software") for t in cv.get("software") or []]
        for name, cat in terms:
            name = (name or "").strip()[:120]
            if not name:
                continue
            if name.lower() in existing:
                out["skipped_duplicates"] += 1
                continue
            existing.add(name.lower())
            db.add(Skill(profile_id=profile.id, name=name, category=cat,
                         confirmed_by_candidate=False, source="cv_extraction"))
            out["skills"] += 1

    if opts.get("experience", True):
        by_key = {_key(w.employer, w.position): w for w in profile.work_experience}
        for e in cv.get("experience") or []:
            employer = (e.get("employer") or "").strip()
            if not employer:
                continue
            bullets = "\n".join(b for b in e.get("bullets") or [] if b)
            start, end = _to_date(e.get("start")), None if e.get("is_current") else _to_date(e.get("end"))
            match = by_key.get(_key(employer, e.get("position")))
            if match is not None:
                if match.confirmed_by_candidate:
                    out["skipped_duplicates"] += 1
                    continue
                changed = False
                for attr, val in (("start_date", start), ("end_date", end), ("responsibilities", bullets or None)):
                    if val and not getattr(match, attr):
                        setattr(match, attr, val)
                        changed = True
                if e.get("is_current") and not match.is_current:
                    match.is_current, changed = True, True
                out["work_experience_updated" if changed else "skipped_duplicates"] += 1
                continue
            db.add(WorkExperience(profile_id=profile.id, employer=employer[:200],
                                  position=(e.get("position") or None) and e["position"][:200],
                                  start_date=start, end_date=end, is_current=bool(e.get("is_current")),
                                  responsibilities=bullets or None,
                                  confirmed_by_candidate=False, source="cv_extraction"))
            out["work_experience"] += 1

    if opts.get("education", True):
        have = {_key(ed.qualification.split(" (")[0] if ed.qualification else "", ed.institution)
                for ed in profile.education}
        for ed in (cv.get("education") or []) + (cv.get("current_studies") or []):
            qual = (ed.get("qualification") or "").strip()
            inst = (ed.get("institution") or "").strip()
            if not inst:
                continue
            if _key(qual, inst) in have:
                out["skipped_duplicates"] += 1
                continue
            have.add(_key(qual, inst))
            status = ed.get("status") or "completed"
            title = (qual + _STATUS_SUFFIX.get(status, "")) if qual else None
            completed = status == "completed" and ed.get("year")
            from datetime import date as _d
            db.add(Education(profile_id=profile.id, institution=inst[:200], qualification=title and title[:200],
                             completion_date=_d(int(ed["year"]), 12, 1) if completed else None,
                             confirmed_by_candidate=False, source="cv_extraction"))
            out["education"] += 1

    if opts.get("certifications", True):
        have = {c.name.split(" (")[0].lower() for c in profile.certifications}
        for c in (cv.get("certifications") or []) + (cv.get("short_courses") or []) + \
                 (cv.get("in_progress_certs") or []):
            name = (c.get("name") or "").strip()
            if not name:
                continue
            if name.lower() in have:
                out["skipped_duplicates"] += 1
                continue
            have.add(name.lower())
            title = name + (" (in progress)" if c.get("status") == "in_progress" else "")
            db.add(Certification(profile_id=profile.id, name=title[:200],
                                 issuing_organization=(c.get("issuer") or None) and c["issuer"][:200],
                                 issue_date=_to_date(c.get("year")) if c.get("status") != "in_progress" else None,
                                 confirmed_by_candidate=False, source="cv_extraction"))
            out["certifications"] += 1

    db.commit()
    return out
