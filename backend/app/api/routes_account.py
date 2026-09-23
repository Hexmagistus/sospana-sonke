"""POPIA data-subject rights: access/export (s23) and erasure (s24) of the caller's own data."""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.comment import CompanyComment
from app.models.message import Message, UserBlock, MessageReport
from app.models.notification import Notification, PushToken
from app.models.user import User
from app.models.cv import CV
from app.models.document import CVVersion, CoverLetter
from app.models.profile import CandidateProfile, Education, Certification, WorkExperience, Skill

router = APIRouter(tags=["account"])


class DeleteRequest(BaseModel):
    password: str


@router.get("/account/export")
@limiter.limit("5/hour")
def export_my_data(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """A machine-readable copy of the personal data held about the caller."""
    now = datetime.now(timezone.utc)
    msgs = (db.query(Message)
            .filter(or_(Message.sender_id == user.id, Message.recipient_id == user.id), Message.expires_at > now)
            .order_by(Message.created_at).all())
    return {
        "exported_at": now.isoformat(),
        "account": {
            "id": user.id, "email": user.email, "first_name": user.first_name, "last_name": user.last_name,
            "mobile_number": user.mobile_number, "preferred_position": user.preferred_position,
            "qualification_name": user.qualification_name, "role": user.role,
            "email_verified": user.email_verified, "mfa_enabled": user.mfa_enabled,
            "allow_messages": user.allow_messages,
            "policy_version": user.policy_version,
            "policy_accepted_at": user.policy_accepted_at.isoformat() if user.policy_accepted_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "temporary_messages": [
            {"direction": "sent" if m.sender_id == user.id else "received", "body": m.body,
             "sent_at": m.created_at.isoformat() if m.created_at else None,
             "expires_at": m.expires_at.isoformat() if m.expires_at else None}
            for m in msgs
        ],
        "community_tips": [
            {"company_id": c.company_id, "kind": c.kind, "body": c.body,
             "posted_at": c.created_at.isoformat() if c.created_at else None}
            for c in db.query(CompanyComment).filter(CompanyComment.user_id == user.id)
        ],
        "blocked_user_ids": [b.blocked_id for b in db.query(UserBlock).filter(UserBlock.blocker_id == user.id)],
        "note": "Temporary messages are deleted automatically 24 hours after they are sent. "
                "Your CV, profile, applications and other records can be requested from the Information Officer.",
    }


def _erase_documents_and_profile(db: Session, user: User) -> None:
    """POPIA erasure for everything CV-shaped: stored file bytes (uploaded CVs,
    generated CVs/cover letters) are deleted, their extracted text/content is
    wiped, and the candidate profile (education, work history, skills,
    certifications) is removed. Rows that other records point at are kept as
    empty, soft-deleted shells so foreign keys stay valid."""
    import logging
    from app.services.storage import get_storage
    storage = get_storage()
    now = datetime.now(timezone.utc)

    def drop(key):
        if key:
            try:
                storage.delete(key)
            except Exception:
                logging.getLogger(__name__).warning("Could not delete stored file %s during erasure", key,
                                                    exc_info=True)

    for cv in db.query(CV).filter(CV.user_id == user.id).all():
        drop(cv.storage_key)
        cv.storage_key, cv.original_filename = "", "deleted"
        cv.extracted_text, cv.structured, cv.parse_error = None, None, None
        cv.deleted_at = cv.deleted_at or now
    for v in db.query(CVVersion).filter(CVVersion.user_id == user.id).all():
        drop(v.storage_key_pdf); drop(v.storage_key_docx)
        v.storage_key_pdf = v.storage_key_docx = None
        v.content, v.label, v.ats_breakdown, v.truthfulness_violations = {}, "deleted", None, None
        v.deleted_at = v.deleted_at or now
    for letter in db.query(CoverLetter).filter(CoverLetter.user_id == user.id).all():
        drop(letter.storage_key_pdf); drop(letter.storage_key_docx)
        letter.storage_key_pdf = letter.storage_key_docx = None
        letter.body, letter.label = "", "deleted"
        letter.deleted_at = letter.deleted_at or now
    for profile in db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).all():
        for child in (Education, Certification, WorkExperience, Skill):
            db.query(child).filter(child.profile_id == profile.id).delete(synchronize_session=False)
        # Null every optional personal field on the profile row itself.
        for col in CandidateProfile.__table__.columns:
            if col.nullable and col.name not in ("id", "user_id", "created_at", "updated_at", "deleted_at"):
                setattr(profile, col.key, None)
        profile.deleted_at = profile.deleted_at or now


@router.post("/account/delete", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
def delete_my_account(request: Request, body: DeleteRequest, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Right to erasure: removes messaging data now and anonymises the account so it can never sign in again."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=403, detail="Password is incorrect.")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Administrator accounts must be removed by another administrator.")
    db.query(Message).filter(or_(Message.sender_id == user.id, Message.recipient_id == user.id)).delete(
        synchronize_session=False)
    db.query(UserBlock).filter(or_(UserBlock.blocker_id == user.id, UserBlock.blocked_id == user.id)).delete(
        synchronize_session=False)
    db.query(MessageReport).filter(MessageReport.reporter_id == user.id).delete(synchronize_session=False)
    db.query(CompanyComment).filter(CompanyComment.user_id == user.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
    db.query(PushToken).filter(PushToken.user_id == user.id).delete(synchronize_session=False)
    _erase_documents_and_profile(db, user)
    user.token_version = (user.token_version or 0) + 1  # kill every session now
    user.email = f"deleted-{user.id}@deleted.invalid"
    user.first_name = "Deleted"
    user.last_name = "User"
    user.mobile_number = None
    user.preferred_position = None
    user.qualification_name = None
    user.mfa_enabled = False
    user.mfa_secret = None
    user.allow_messages = False
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    db.commit()
