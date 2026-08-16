"""CV upload & intelligence (blueprint Step 3).

Uploads are size/type/malware-checked, the original is stored immutably, text is
extracted, and an AI provider produces a structured suggestion the candidate can
review and import into their profile. The original CV is never overwritten.
"""
import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from sqlalchemy.orm import Session

from app.ai import structure_cv_with_fallback
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.cv import CV
from app.models.user import User
from app.schemas.cv import (
    CVResponse, CVStructuredResponse, ApplyToProfileRequest, ApplyToProfileResult,
)
from app.services.cv_extract import extract_text, CVExtractionError
from app.services.malware_scan import scan_upload
from app.services.storage import get_storage
from app.services.profile_service import get_or_create_profile, apply_structured_to_profile

router = APIRouter(prefix="/cv", tags=["cv"])


def _get_owned_cv(db: Session, user: User, cv_id: str) -> CV:
    cv = db.get(CV, cv_id)
    if cv is None or cv.user_id != user.id or cv.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
    return cv


def _process(cv: CV, data: bytes) -> None:
    """Extract text and structure it; mutate the CV record in place (no commit)."""
    try:
        text = extract_text(data, cv.extension)
        cv.extracted_text = text
        cv.parse_status = "extracted"
        structured, model_name = structure_cv_with_fallback(text)
        cv.structured = structured
        cv.ai_model = model_name
        cv.parse_status = "parsed"
        cv.parse_error = None
    except CVExtractionError as exc:
        cv.parse_status = "failed"
        cv.parse_error = str(exc)


@router.post("", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    filename = file.filename or "cv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    data = await file.read()

    scan = scan_upload(data, ext)
    if not scan.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=scan.reason)

    file_hash = hashlib.sha256(data).hexdigest()
    cv = CV(
        user_id=user.id,
        original_filename=filename[:255],
        content_type=file.content_type or "application/octet-stream",
        extension=ext,
        size_bytes=len(data),
        file_hash=file_hash,
        storage_key="",  # set after we have an id
        is_original=True,
    )
    db.add(cv)
    db.flush()  # assigns cv.id without committing

    key = f"cv/{user.id}/{cv.id}.{ext}"
    get_storage().put(key, data)
    cv.storage_key = key

    _process(cv, data)
    db.commit()
    db.refresh(cv)
    return CVResponse.model_validate(cv)


@router.get("", response_model=list[CVResponse])
def list_cvs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(CV)
            .filter(CV.user_id == user.id, CV.deleted_at.is_(None))
            .order_by(CV.created_at.desc()).all())
    return [CVResponse.model_validate(r) for r in rows]


@router.get("/{cv_id}", response_model=CVResponse)
def get_cv(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return CVResponse.model_validate(_get_owned_cv(db, user, cv_id))


@router.get("/{cv_id}/structured", response_model=CVStructuredResponse)
def get_cv_structured(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cv = _get_owned_cv(db, user, cv_id)
    return CVStructuredResponse(cv_id=cv.id, parse_status=cv.parse_status,
                               ai_model=cv.ai_model, structured=cv.structured)


@router.get("/{cv_id}/download")
def download_cv(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cv = _get_owned_cv(db, user, cv_id)
    data = get_storage().get(cv.storage_key)
    return Response(
        content=data,
        media_type=cv.content_type,
        headers={"Content-Disposition": f'attachment; filename="{cv.original_filename}"'},
    )


@router.post("/{cv_id}/reparse", response_model=CVStructuredResponse)
def reparse_cv(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cv = _get_owned_cv(db, user, cv_id)
    data = get_storage().get(cv.storage_key)
    _process(cv, data)
    db.commit()
    db.refresh(cv)
    return CVStructuredResponse(cv_id=cv.id, parse_status=cv.parse_status,
                               ai_model=cv.ai_model, structured=cv.structured)


@router.post("/{cv_id}/apply-to-profile", response_model=ApplyToProfileResult)
def apply_to_profile(cv_id: str, body: ApplyToProfileRequest, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    cv = _get_owned_cv(db, user, cv_id)
    if cv.parse_status != "parsed" or not cv.structured:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="CV has not been parsed successfully; nothing to apply.")
    profile = get_or_create_profile(db, user.id)
    added = apply_structured_to_profile(db, profile, cv.structured, body.model_dump())
    return ApplyToProfileResult(
        skills_added=added["skills"],
        education_added=added["education"],
        work_experience_added=added["work_experience"],
        certifications_added=added["certifications"],
        profile_fields_filled=added["profile_fields"],
    )


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cv(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cv = _get_owned_cv(db, user, cv_id)
    # Soft-delete the record; remove the stored file (data-minimisation, POPIA).
    from datetime import datetime, timezone
    cv.deleted_at = datetime.now(timezone.utc)
    try:
        get_storage().delete(cv.storage_key)
    except Exception:
        pass
    db.commit()
