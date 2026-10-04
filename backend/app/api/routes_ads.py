"""Advertiser spots on the explorer pages.

Public: read the approved ads, and apply for a spot. Admin: list applications
and approve or reject them. Applying stores a pending row and nothing else: no
payment is taken, no email is sent, nothing is published until an admin
approves it.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.ad import AdApplication
from app.models.admin_ops import AdminAuditLog
from app.models.user import User
from app.schemas.ad import (
    AdApplicationAdmin, AdApplicationCreate, AdApplicationReceipt, AdDecision, PublicAd, valid_slot_key,
)

router = APIRouter(prefix="/ads", tags=["ads"])

# Per-address and overall caps on waiting applications. These hold even when the
# per-IP limiter is bypassed, so the admin queue cannot be flooded.
MAX_PENDING_PER_EMAIL = 3
MAX_PENDING_TOTAL = 500


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/slots", response_model=list[PublicAd])
@limiter.limit("120/minute")
def public_slots(request: Request, db: Session = Depends(get_db)):
    """Ads an admin approved and whose run window is open. Empty until one is."""
    now = _now()
    rows = (
        db.query(AdApplication)
        .filter(
            AdApplication.status == "approved",
            AdApplication.deleted_at.is_(None),
            AdApplication.slot_key.isnot(None),
            or_(AdApplication.starts_at.is_(None), AdApplication.starts_at <= now),
            or_(AdApplication.ends_at.is_(None), AdApplication.ends_at > now),
        )
        .order_by(AdApplication.starts_at.asc())
        .all()
    )
    seen: set[str] = set()
    out: list[PublicAd] = []
    for r in rows:  # one ad per slot
        if r.slot_key in seen:
            continue
        seen.add(r.slot_key)
        out.append(PublicAd(slot_key=r.slot_key, business_name=r.business_name, ad_text=r.ad_text, website=r.website))
    return out


@router.post("/applications", response_model=AdApplicationReceipt, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def apply_for_spot(request: Request, body: AdApplicationCreate, db: Session = Depends(get_db)):
    email = str(body.contact_email).strip().lower()
    waiting = db.query(func.count(AdApplication.id)).filter(AdApplication.status == "pending")
    if waiting.scalar() >= MAX_PENDING_TOTAL:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="We are not taking new applications right now. Please try again later.")
    if waiting.filter(func.lower(AdApplication.contact_email) == email).scalar() >= MAX_PENDING_PER_EMAIL:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="You already have applications waiting for review. We will reply by email.")
    row = AdApplication(
        business_name=body.business_name,
        contact_email=email,
        website=body.website,
        ad_text=body.ad_text,
        amount_usd_per_day=body.amount_usd_per_day,
        days=body.days,
        requested_slot=body.requested_slot,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return AdApplicationReceipt(
        id=row.id,
        status=row.status,
        total_usd=(Decimal(body.amount_usd_per_day) * body.days).quantize(Decimal("0.01")),
        message=(
            "Thank you. Your application is waiting for review. Nothing has been charged. "
            "If it is approved we will email you payment instructions."
        ),
    )


@router.get("/admin/applications", response_model=list[AdApplicationAdmin])
def admin_list(status_filter: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    q = db.query(AdApplication).filter(AdApplication.deleted_at.is_(None))
    if status_filter:
        q = q.filter(AdApplication.status == status_filter)
    return q.order_by(AdApplication.created_at.desc()).limit(300).all()


@router.patch("/admin/applications/{app_id}", response_model=AdApplicationAdmin)
def admin_decide(app_id: str, body: AdDecision, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    row = db.get(AdApplication, app_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Application not found.")
    if body.status == "approved":
        slot = body.slot_key or row.slot_key or row.requested_slot
        if not slot or not valid_slot_key(slot):
            raise HTTPException(status_code=422, detail="Choose a valid slot (L1-L10 or R1-R10) to approve.")
        now = _now()
        clash = (
            db.query(AdApplication)
            .filter(
                AdApplication.id != row.id,
                AdApplication.status == "approved",
                AdApplication.slot_key == slot,
                AdApplication.deleted_at.is_(None),
                or_(AdApplication.ends_at.is_(None), AdApplication.ends_at > now),
            )
            .first()
        )
        if clash is not None:
            raise HTTPException(status_code=409, detail=f"Slot {slot} already has a running ad.")
        row.slot_key = slot
        row.starts_at = now
        row.ends_at = now + timedelta(days=row.days)
    else:
        row.slot_key = None
        row.starts_at = None
        row.ends_at = None
    row.status = body.status
    row.admin_note = body.admin_note
    db.add(AdminAuditLog(admin_id=admin.id, action=f"ad_{body.status}"[:40], target_user_id=None,
                         detail=f"application {row.id} slot {row.slot_key or '-'}"[:500]))
    db.commit()
    db.refresh(row)
    return row
