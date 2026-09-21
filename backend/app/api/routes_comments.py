"""Community tips under employer links: quick status tags + short tips, so others decide faster.

Tips are public to every visitor and expire 5 days after posting; only signed-in members can post."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional, require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.comment import CompanyComment, CommentFlag, COMMENT_KINDS, COMMENT_TTL_DAYS
from app.models.company import Company
from app.models.message import UserBlock
from app.services.notification_service import create_notification
from app.models.user import User
from app.services.message_filter import check_message

router = APIRouter(tags=["comments"])

MAX_PER_DAY = 30
MAX_PER_COMPANY = 200
HIDE_AT_FLAGS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def purge_expired_comments(db: Session) -> int:
    n = db.query(CompanyComment).filter(CompanyComment.expires_at <= _now()).delete(synchronize_session=False)
    db.commit()
    return n


def _name(u: User | None) -> str:
    if not u:
        return "Member"
    last = (u.last_name or "").strip()
    return f"{u.first_name} {last[:1]}." if last else u.first_name


class CommentOut(BaseModel):
    id: str
    kind: str
    body: str | None
    author: str
    mine: bool
    created_at: datetime


class CommentsResponse(BaseModel):
    counts: dict[str, int]
    comments: list[CommentOut]


class CommentIn(BaseModel):
    kind: str
    body: str | None = Field(default=None, max_length=300)
    mentions: list[str] = Field(default_factory=list, max_length=3)  # tagged member ids (opt-in members only)


def _visible(db: Session, company_id: str):
    return db.query(CompanyComment).filter(
        CompanyComment.company_id == company_id, CompanyComment.hidden.is_(False),
        CompanyComment.expires_at > _now(),
    )


def _notify_mentions(db: Session, c: CompanyComment, author: User, company: Company, ids: list[str]) -> None:
    """In-app notice to tagged members. Only opted-in (allow_messages), active, non-blocking members can be tagged."""
    for uid in dict.fromkeys(ids):
        if uid == author.id:
            continue
        target = db.get(User, uid)
        if not target or not target.is_active or target.deleted_at is not None or not target.allow_messages:
            continue
        if db.query(UserBlock.id).filter(
                ((UserBlock.blocker_id == uid) & (UserBlock.blocked_id == author.id)) |
                ((UserBlock.blocker_id == author.id) & (UserBlock.blocked_id == uid))).first():
            continue
        create_notification(
            db, user_id=uid, to_email=None, type="mention",
            title=f"{_name(author)} tagged you on {company.company_name}",
            body=(c.body or "See the tip on this employer's link.")[:200],
            related_type="comment", related_id=c.id, send_email=False,
            link_url=f"/companies?company={company.id}",
        )
    db.commit()


@router.get("/comments/summary")
def summary(db: Session = Depends(get_db)):
    """{company_id: {"total": n, "works": n}} for card badges."""
    rows = (db.query(CompanyComment.company_id, CompanyComment.kind, func.count())
            .filter(CompanyComment.hidden.is_(False), CompanyComment.expires_at > _now())
            .group_by(CompanyComment.company_id, CompanyComment.kind).all())
    out: dict[str, dict[str, int]] = {}
    for cid, kind, n in rows:
        d = out.setdefault(cid, {"total": 0, "works": 0, "broken": 0})
        d["total"] += n
        if kind in ("works", "broken"):
            d[kind] += n
    return out


@router.get("/companies/{company_id}/comments", response_model=CommentsResponse)
def list_comments(company_id: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    purge_expired_comments(db)
    rows = _visible(db, company_id).order_by(CompanyComment.created_at.desc()).limit(50).all()
    users = {u.id: u for u in db.query(User).filter(User.id.in_({r.user_id for r in rows})).all()} if rows else {}
    counts = {k: 0 for k in COMMENT_KINDS}
    for r in _visible(db, company_id).all():
        counts[r.kind] = counts.get(r.kind, 0) + 1
    return CommentsResponse(counts=counts, comments=[
        CommentOut(id=r.id, kind=r.kind, body=r.body, author=_name(users.get(r.user_id)),
                   mine=bool(user and r.user_id == user.id), created_at=r.created_at) for r in rows
    ])


@router.post("/companies/{company_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def add_comment(request: Request, company_id: str, body: CommentIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if user.messaging_banned:
        raise HTTPException(403, "Your posting privileges are suspended.")
    if body.kind not in COMMENT_KINDS:
        raise HTTPException(422, "Unknown tag.")
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found.")
    text = (body.body or "").strip() or None
    if body.kind == "tip" and not text:
        raise HTTPException(422, "Write a short tip.")
    if text:
        problem = check_message(text)
        if problem:
            raise HTTPException(422, problem.replace("messages", "tips").replace("Message", "Tip"))
    since = _now() - timedelta(days=1)
    if db.query(CompanyComment).filter(CompanyComment.user_id == user.id, CompanyComment.created_at >= since).count() >= MAX_PER_DAY:
        raise HTTPException(429, "Daily tip limit reached. Try again tomorrow.")
    if db.query(CompanyComment).filter(CompanyComment.company_id == company_id).count() >= MAX_PER_COMPANY:
        raise HTTPException(429, "This employer already has plenty of tips.")
    c = CompanyComment(company_id=company_id, user_id=user.id, kind=body.kind, body=text,
                       expires_at=_now() + timedelta(days=COMMENT_TTL_DAYS))
    db.add(c)
    db.commit()
    db.refresh(c)
    _notify_mentions(db, c, user, company, body.mentions)
    return CommentOut(id=c.id, kind=c.kind, body=c.body, author=_name(user), mine=True, created_at=c.created_at)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(CompanyComment, comment_id)
    if not c or (c.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Not found.")
    db.delete(c)
    db.commit()


@router.post("/comments/{comment_id}/flag", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/hour")
def flag_comment(request: Request, comment_id: str, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    c = db.get(CompanyComment, comment_id)
    if not c or c.user_id == user.id:
        raise HTTPException(404, "Not found.")
    if not db.query(CommentFlag).filter_by(comment_id=c.id, user_id=user.id).first():
        db.add(CommentFlag(comment_id=c.id, user_id=user.id))
        db.flush()
        if db.query(CommentFlag).filter_by(comment_id=c.id).count() >= HIDE_AT_FLAGS:
            c.hidden = True
    db.commit()


@router.get("/admin/comments/flagged")
def admin_flagged(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    ids = [r[0] for r in db.query(CommentFlag.comment_id).distinct().all()]
    rows = db.query(CompanyComment).filter(CompanyComment.id.in_(ids)).order_by(CompanyComment.created_at.desc()).limit(100).all() if ids else []
    return [{"id": r.id, "company_id": r.company_id, "kind": r.kind, "body": r.body, "hidden": r.hidden,
             "flags": db.query(CommentFlag).filter_by(comment_id=r.id).count()} for r in rows]


@router.post("/admin/comments/{comment_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def admin_restore(comment_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    c = db.get(CompanyComment, comment_id)
    if not c:
        raise HTTPException(404, "Not found.")
    db.query(CommentFlag).filter_by(comment_id=c.id).delete()
    c.hidden = False
    db.commit()
