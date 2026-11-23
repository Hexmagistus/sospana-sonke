"""Gauteng Hustle Run tester access (Google Play closed test).

Public:
  POST /game/tester-requests            leave a Google account email (no email is sent)
Admin only (``require_admin``):
  GET  /admin/game/tester-requests       JSON list, ``?status=pending|added|all``
  GET  /admin/game/tester-requests/export   text/csv, one email per line (pending by default)
  POST /admin/game/tester-requests/mark-added   ``{"emails": [...]}`` or ``{"all_pending": true}``
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_optional, require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.game_tester import GameTesterRequest
from app.models.user import User

router = APIRouter(prefix="/game", tags=["game"])
admin_router = APIRouter(prefix="/admin/game", tags=["game"])

# Deliberately simple and strict: one @, a dot in the domain, no spaces or
# angle brackets. Google accounts are usually @gmail.com but Workspace and
# other addresses can be Google accounts too, so the domain is not checked.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")

SUCCESS_MESSAGE = "You're on the list. We'll add you within about 24-48 hours, then open the download link again."


def normalise_email(raw: str) -> str | None:
    email = (raw or "").strip().lower()
    if not email or len(email) > 254 or not _EMAIL_RE.match(email):
        return None
    local, _, domain = email.rpartition("@")
    if len(local) > 64 or ".." in email or domain.endswith("."):
        return None
    return email


class TesterRequestIn(BaseModel):
    email: str = Field(..., max_length=320)
    name: str | None = Field(default=None, max_length=200)
    # Honeypot: a hidden field real people never fill in.
    website: str | None = Field(default=None, max_length=500)


class TesterRequestOut(BaseModel):
    ok: bool = True
    message: str = SUCCESS_MESSAGE


@router.post("/tester-requests", response_model=TesterRequestOut)
@limiter.limit("5/minute;20/hour")
def request_tester_access(
    request: Request,
    body: TesterRequestIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    # A bot filled the hidden field: answer exactly like a success, store nothing.
    if body.website and body.website.strip():
        return TesterRequestOut()
    email = normalise_email(body.email)
    if email is None:
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")
    name = (body.name or "").strip()[:120] or None

    existing = (
        db.query(GameTesterRequest)
        .filter(func.lower(GameTesterRequest.email) == email)
        .first()
    )
    if existing is not None:
        # Duplicate-safe: resubmitting just shows the same success message.
        changed = False
        if name and not existing.name:
            existing.name, changed = name, True
        if user is not None and not existing.user_id:
            existing.user_id, changed = user.id, True
        if changed:
            db.commit()
        return TesterRequestOut()

    db.add(GameTesterRequest(email=email, name=name, user_id=user.id if user else None))
    try:
        db.commit()
    except IntegrityError:
        # Two submits raced on the unique lower(email) index: already on the list.
        db.rollback()
    return TesterRequestOut()


class TesterRequestRow(BaseModel):
    id: str
    email: str
    name: str | None
    user_id: str | None
    status: str
    created_at: datetime | None
    added_at: datetime | None

    model_config = {"from_attributes": True}


def _rows(db: Session, status: str):
    q = db.query(GameTesterRequest)
    if status != "all":
        q = q.filter(GameTesterRequest.status == status)
    return q.order_by(GameTesterRequest.created_at.asc(), GameTesterRequest.email.asc())


@admin_router.get("/tester-requests", response_model=list[TesterRequestRow])
def list_tester_requests(
    status: str = Query("pending", pattern="^(pending|added|all)$"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return [TesterRequestRow.model_validate(r) for r in _rows(db, status).limit(limit).all()]


@admin_router.get("/tester-requests/export", response_class=PlainTextResponse)
def export_tester_requests(
    status: str = Query("pending", pattern="^(pending|added|all)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """One email per line, no header: the format Play Console's tester list accepts."""
    emails = [r.email for r in _rows(db, status).all()]
    body = "\n".join(emails) + ("\n" if emails else "")
    return PlainTextResponse(
        body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="hustle-run-testers-{status}.csv"',
            "Cache-Control": "no-store",
        },
    )


class MarkAddedIn(BaseModel):
    emails: list[str] = Field(default_factory=list, max_length=5000)
    all_pending: bool = False


class MarkAddedOut(BaseModel):
    updated: int


@admin_router.post("/tester-requests/mark-added", response_model=MarkAddedOut)
def mark_tester_requests_added(
    body: MarkAddedIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(GameTesterRequest).filter(GameTesterRequest.status == "pending")
    if not body.all_pending:
        wanted = {e for e in (normalise_email(x) for x in body.emails) if e}
        if not wanted:
            return MarkAddedOut(updated=0)
        q = q.filter(func.lower(GameTesterRequest.email).in_(wanted))
    now = datetime.now(timezone.utc)
    updated = 0
    for row in q.all():
        row.status = "added"
        row.added_at = now
        updated += 1
    db.commit()
    return MarkAddedOut(updated=updated)
