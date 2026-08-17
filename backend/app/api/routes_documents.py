"""Document generation routes (blueprint Steps 7, 11, 12).

Candidates generate a tailored CV / cover letter from one of their matches, then
list and download them. All endpoints are ownership-scoped.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.document import CVVersion, CoverLetter
from app.models.user import User
from app.schemas.document import CVVersionResponse, CoverLetterResponse
from pydantic import BaseModel
from app.services.document_service import (
    generate_cv_for_match, generate_cover_letter_for_match,
    generate_cv_for_target, generate_cover_letter_for_target,
)
from app.services.storage import get_storage
from app.services.subscription_service import require_active_subscription

router = APIRouter(tags=["documents"])

_PDF = "application/pdf"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/matches/{match_id}/generate-cv", response_model=CVVersionResponse,
             status_code=status.HTTP_201_CREATED)
def generate_cv(match_id: str, db: Session = Depends(get_db),
                user: User = Depends(require_active_subscription)):
    return CVVersionResponse.model_validate(generate_cv_for_match(db, user, match_id))


@router.post("/matches/{match_id}/generate-cover-letter", response_model=CoverLetterResponse,
             status_code=status.HTTP_201_CREATED)
def generate_cover_letter(match_id: str, db: Session = Depends(get_db),
                          user: User = Depends(require_active_subscription)):
    return CoverLetterResponse.model_validate(generate_cover_letter_for_match(db, user, match_id))


class TailorRequest(BaseModel):
    job_title: str | None = None
    company_name: str | None = None
    job_description: str | None = None


@router.post("/tailor", status_code=status.HTTP_201_CREATED)
def tailor_for_any_job(body: TailorRequest, db: Session = Depends(get_db),
                       user: User = Depends(require_active_subscription)):
    """Generate a tailored CV + cover letter for any job the candidate provides
    (a pasted ad or a chosen employer) — no scraped vacancy required."""
    cv = generate_cv_for_target(db, user, body.job_title, body.company_name, body.job_description)
    letter = generate_cover_letter_for_target(db, user, body.job_title, body.company_name, body.job_description)
    return {
        "cv_version": CVVersionResponse.model_validate(cv),
        "cover_letter": CoverLetterResponse.model_validate(letter),
    }


@router.get("/cv-versions", response_model=list[CVVersionResponse])
def list_cv_versions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(CVVersion).filter(CVVersion.user_id == user.id, CVVersion.deleted_at.is_(None))
            .order_by(CVVersion.created_at.desc()).all())
    return [CVVersionResponse.model_validate(r) for r in rows]


@router.get("/cv-versions/{version_id}", response_model=CVVersionResponse)
def get_cv_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    v = db.get(CVVersion, version_id)
    if v is None or v.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV version not found.")
    return CVVersionResponse.model_validate(v)


@router.get("/cv-versions/{version_id}/download")
def download_cv_version(version_id: str, fmt: str = Query(default="pdf", pattern="^(pdf|docx)$"),
                        db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    v = db.get(CVVersion, version_id)
    if v is None or v.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV version not found.")
    key = v.storage_key_pdf if fmt == "pdf" else v.storage_key_docx
    media = _PDF if fmt == "pdf" else _DOCX
    data = get_storage().get(key)
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{v.label}.{fmt}"'})


@router.get("/cover-letters", response_model=list[CoverLetterResponse])
def list_cover_letters(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(CoverLetter).filter(CoverLetter.user_id == user.id, CoverLetter.deleted_at.is_(None))
            .order_by(CoverLetter.created_at.desc()).all())
    return [CoverLetterResponse.model_validate(r) for r in rows]


@router.get("/cover-letters/{letter_id}/download")
def download_cover_letter(letter_id: str, fmt: str = Query(default="pdf", pattern="^(pdf|docx)$"),
                          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    letter = db.get(CoverLetter, letter_id)
    if letter is None or letter.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found.")
    key = letter.storage_key_pdf if fmt == "pdf" else letter.storage_key_docx
    media = _PDF if fmt == "pdf" else _DOCX
    data = get_storage().get(key)
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{letter.label}.{fmt}"'})
