"""Temporary user-to-user messages (24h auto-delete), blocking, reporting and admin review.

POPIA notes: opt-in recipients; only first name + last initial are ever shown to
other users; no email/phone exposure; messages are deleted after 24h; reported
messages are preserved as a snapshot for admin review and purged after 30 days.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.message import (
    Message, UserBlock, MessageReport, MESSAGE_TTL_HOURS, REPORT_RETENTION_DAYS,
)
from app.models.user import User
from app.services.message_filter import check_message

router = APIRouter(tags=["messages"])

REASONS = {"harassment", "scam", "spam", "inappropriate", "other"}
MAX_PER_DAY = 60          # per sender
MAX_PER_RECIPIENT_DAY = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


def purge_expired(db: Session) -> int:
    """Hard-delete expired messages and reports past their retention window."""
    now = _now()
    n = db.query(Message).filter(Message.expires_at <= now).delete(synchronize_session=False)
    db.query(MessageReport).filter(MessageReport.purge_after <= now).delete(synchronize_session=False)
    db.commit()
    return n


def _display_name(u: User) -> str:
    last = (u.last_name or "").strip()
    return f"{u.first_name} {last[:1]}." if last else u.first_name


def _blocked_between(db: Session, a: str, b: str) -> bool:
    return db.query(UserBlock.id).filter(
        or_(and_(UserBlock.blocker_id == a, UserBlock.blocked_id == b),
            and_(UserBlock.blocker_id == b, UserBlock.blocked_id == a))
    ).first() is not None


class MessageOut(BaseModel):
    id: str
    other_user_id: str
    other_name: str
    body: str
    direction: str            # "in" | "out"
    created_at: datetime
    expires_at: datetime
    read: bool


class DirectoryEntry(BaseModel):
    id: str
    name: str


class MemberEntry(BaseModel):
    id: str
    name: str
    position: str | None = None


class SendRequest(BaseModel):
    recipient_id: str
    body: str = Field(min_length=1, max_length=500)


class SettingsBody(BaseModel):
    allow_messages: bool


class ReportBody(BaseModel):
    reason: str
    note: str | None = Field(default=None, max_length=500)


def _to_out(m: Message, me: User, other: User) -> MessageOut:
    incoming = m.recipient_id == me.id
    return MessageOut(
        id=m.id, other_user_id=other.id, other_name=_display_name(other), body=m.body,
        direction="in" if incoming else "out", created_at=m.created_at, expires_at=m.expires_at,
        read=(m.read_at is not None) if incoming else True,
    )


# ---- settings ----

@router.get("/messages/settings")
def get_settings(user: User = Depends(get_current_user)):
    return {"allow_messages": bool(user.allow_messages), "messaging_banned": bool(user.messaging_banned),
            "ttl_hours": MESSAGE_TTL_HOURS}


@router.put("/messages/settings")
def put_settings(body: SettingsBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.allow_messages = body.allow_messages
    db.commit()
    return {"allow_messages": bool(user.allow_messages), "messaging_banned": bool(user.messaging_banned),
            "ttl_hours": MESSAGE_TTL_HOURS}


# ---- directory (opt-in users only, name-only) ----

@router.get("/messages/directory", response_model=list[DirectoryEntry])
@limiter.limit("30/minute")
def directory(request: Request, q: str = Query(min_length=2, max_length=50),
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    needle = f"%{q.strip().lower()}%"
    blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)
    blockers = select(UserBlock.blocker_id).where(UserBlock.blocked_id == user.id)
    rows = (
        db.query(User)
        .filter(
            User.allow_messages.is_(True), User.is_active.is_(True), User.deleted_at.is_(None),
            User.id != user.id, ~User.id.in_(blocked), ~User.id.in_(blockers),
            or_(func.lower(User.first_name).like(needle), func.lower(User.last_name).like(needle)),
        )
        .order_by(User.first_name, User.last_name)
        .limit(20)
        .all()
    )
    return [DirectoryEntry(id=u.id, name=_display_name(u)) for u in rows]


@router.get("/messages/members", response_model=list[MemberEntry])
@limiter.limit("30/minute")
def members(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Opted-in members (name + desired position) for the tag dropdown."""
    blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)
    blockers = select(UserBlock.blocker_id).where(UserBlock.blocked_id == user.id)
    rows = (
        db.query(User)
        .filter(User.allow_messages.is_(True), User.is_active.is_(True), User.deleted_at.is_(None),
                User.id != user.id, ~User.id.in_(blocked), ~User.id.in_(blockers))
        .order_by(User.first_name, User.last_name).limit(300).all()
    )
    return [MemberEntry(id=u.id, name=_display_name(u),
                        position=((u.preferred_position or "").strip() or None)) for u in rows]


# ---- send / read / delete ----

@router.post("/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def send_message(request: Request, body: SendRequest, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    purge_expired(db)
    if user.messaging_banned:
        raise HTTPException(status_code=403, detail="Your messaging access has been suspended after a report.")
    recipient = db.get(User, body.recipient_id)
    generic = HTTPException(status_code=404, detail="This person can't receive messages.")
    if (recipient is None or recipient.id == user.id or not recipient.is_active
            or recipient.deleted_at is not None or not recipient.allow_messages):
        raise generic
    if _blocked_between(db, user.id, recipient.id):
        raise generic
    problem = check_message(body.body)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    since = _now() - timedelta(hours=24)
    sent_today = db.query(func.count(Message.id)).filter(Message.sender_id == user.id, Message.created_at >= since).scalar() or 0
    if sent_today >= MAX_PER_DAY:
        raise HTTPException(status_code=429, detail="Daily message limit reached. Try again tomorrow.")
    to_them = db.query(func.count(Message.id)).filter(
        Message.sender_id == user.id, Message.recipient_id == recipient.id, Message.created_at >= since).scalar() or 0
    if to_them >= MAX_PER_RECIPIENT_DAY:
        raise HTTPException(status_code=429, detail="You've sent this person several messages already. Please wait.")
    msg = Message(sender_id=user.id, recipient_id=recipient.id, body=body.body.strip(),
                  expires_at=_now() + timedelta(hours=MESSAGE_TTL_HOURS))
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _to_out(msg, user, recipient)


def _box(db: Session, user: User, incoming: bool) -> list[MessageOut]:
    purge_expired(db)
    col = Message.recipient_id if incoming else Message.sender_id
    other_col = Message.sender_id if incoming else Message.recipient_id
    blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)
    msgs = (db.query(Message).filter(col == user.id, Message.expires_at > _now(), ~other_col.in_(blocked))
            .order_by(Message.created_at.desc()).limit(100).all())
    ids = {m.sender_id if incoming else m.recipient_id for m in msgs}
    people = {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}
    out = []
    for m in msgs:
        other = people.get(m.sender_id if incoming else m.recipient_id)
        if other is not None:
            out.append(_to_out(m, user, other))
    return out


@router.get("/messages/inbox", response_model=list[MessageOut])
def inbox(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _box(db, user, True)


@router.get("/messages/sent", response_model=list[MessageOut])
def sent(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _box(db, user, False)


@router.get("/messages/unread-count")
def messages_unread(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = (db.query(func.count(Message.id))
         .filter(Message.recipient_id == user.id, Message.read_at.is_(None), Message.expires_at > _now())
         .scalar() or 0)
    return {"unread": n}


@router.post("/messages/{message_id}/read")
def mark_message_read(message_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.get(Message, message_id)
    if m is None or m.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found.")
    if m.read_at is None:
        m.read_at = _now()
        db.commit()
    return {"ok": True}


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.get(Message, message_id)
    if m is None or user.id not in (m.sender_id, m.recipient_id):
        raise HTTPException(status_code=404, detail="Message not found.")
    db.delete(m)
    db.commit()


# ---- block / report ----

@router.get("/messages/blocks", response_model=list[DirectoryEntry])
def list_blocks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(User).join(UserBlock, UserBlock.blocked_id == User.id)
            .filter(UserBlock.blocker_id == user.id).all())
    return [DirectoryEntry(id=u.id, name=_display_name(u)) for u in rows]


@router.post("/messages/blocks/{other_id}", status_code=204)
def block_user(other_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if other_id == user.id or db.get(User, other_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    exists = db.query(UserBlock.id).filter(UserBlock.blocker_id == user.id, UserBlock.blocked_id == other_id).first()
    if not exists:
        db.add(UserBlock(blocker_id=user.id, blocked_id=other_id))
    # Remove anything they already sent us.
    db.query(Message).filter(Message.sender_id == other_id, Message.recipient_id == user.id).delete(
        synchronize_session=False)
    db.commit()


@router.delete("/messages/blocks/{other_id}", status_code=204)
def unblock_user(other_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(UserBlock).filter(UserBlock.blocker_id == user.id, UserBlock.blocked_id == other_id).delete(
        synchronize_session=False)
    db.commit()


@router.post("/messages/{message_id}/report", status_code=201)
@limiter.limit("20/hour")
def report_message(request: Request, message_id: str, body: ReportBody, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    if body.reason not in REASONS:
        raise HTTPException(status_code=422, detail=f"Reason must be one of: {', '.join(sorted(REASONS))}.")
    m = db.get(Message, message_id)
    if m is None or m.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found.")
    db.add(MessageReport(
        reporter_id=user.id, sender_id=m.sender_id, body_snapshot=m.body, reason=body.reason,
        note=(body.note or None), purge_after=_now() + timedelta(days=REPORT_RETENTION_DAYS),
    ))
    # Reporting also blocks the sender and removes the message from the reporter's inbox.
    if not db.query(UserBlock.id).filter(UserBlock.blocker_id == user.id, UserBlock.blocked_id == m.sender_id).first():
        db.add(UserBlock(blocker_id=user.id, blocked_id=m.sender_id))
    db.delete(m)
    db.commit()
    return {"ok": True}


# ---- admin review ----

class ReportOut(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    sender_banned: bool
    reason: str
    note: str | None
    body_snapshot: str
    status: str
    created_at: datetime
    purge_after: datetime


@router.get("/admin/message-reports", response_model=list[ReportOut])
def admin_reports(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    purge_expired(db)
    rows = db.query(MessageReport).order_by(MessageReport.created_at.desc()).limit(200).all()
    ids = {r.sender_id for r in rows}
    people = {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}
    out = []
    for r in rows:
        s = people.get(r.sender_id)
        out.append(ReportOut(
            id=r.id, sender_id=r.sender_id, sender_name=(_display_name(s) if s else "Deleted user"),
            sender_banned=bool(s and s.messaging_banned), reason=r.reason, note=r.note,
            body_snapshot=r.body_snapshot, status=r.status, created_at=r.created_at, purge_after=r.purge_after,
        ))
    return out


class ResolveBody(BaseModel):
    action: str  # dismiss | suspend_sender


@router.post("/admin/message-reports/{report_id}/resolve", response_model=ReportOut)
def admin_resolve(report_id: str, body: ResolveBody, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    r = db.get(MessageReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if body.action not in ("dismiss", "suspend_sender"):
        raise HTTPException(status_code=422, detail="action must be dismiss or suspend_sender.")
    sender = db.get(User, r.sender_id)
    if body.action == "suspend_sender" and sender is not None:
        sender.messaging_banned = True
        r.status = "actioned"
    else:
        r.status = "dismissed"
    r.resolved = True
    db.commit()
    return ReportOut(
        id=r.id, sender_id=r.sender_id, sender_name=(_display_name(sender) if sender else "Deleted user"),
        sender_banned=bool(sender and sender.messaging_banned), reason=r.reason, note=r.note,
        body_snapshot=r.body_snapshot, status=r.status, created_at=r.created_at, purge_after=r.purge_after,
    )
