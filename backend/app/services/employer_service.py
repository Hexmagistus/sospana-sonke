"""Organisation claims, posts, plan prices, and featured placement.

Sponsored rows are chosen after the organic query. They have to match the same
filters, they are capped, and they are returned beside the organic list. The
organic order is left as the caller built it.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone, date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.organisation import (
    PAID_PLAN_CODES,
    EmployerAccount,
    EmployerAuditEvent,
    EmployerCorrection,
    EmployerEntitlement,
    EmployerInvoice,
    EmployerOpportunity,
    EmployerPaymentEvent,
    EmployerPlanConfig,
)
from app.models.usage_count import UsageClickDaily
from app.models.user import User
from app.models.vacancy import Vacancy, VacancySource
from app.services.employer_domain import application_host_allowed, email_matches_company
from app.services.opportunity_type import OPPORTUNITY_TYPES

SPONSORED_CAP = 2
EMPLOYER_ATS = "employer_submitted"
CORRECTION_FIELDS = ("careers_url", "official_website")
RANKING_NOTE = (
    "Sponsored rows are a separate list. They match these filters, they are capped, "
    "and the order of the other rows is unchanged."
)

_PLAN_DEFAULTS = (
    {
        "id": "plan-free",
        "plan_code": "free",
        "amount_zar": 0,
        "post_limit": 3,
        "duration_days": None,
        "label": "Free",
        "owner_note": "Included. No charge.",
        "published": True,
        "includes": (
            "Claim the employer page, submit corrections, and post a limited number of opportunities. "
            "Every post is checked before it is listed."
        ),
    },
    {
        "id": "plan-pro",
        "plan_code": "pro",
        "amount_zar": None,
        "post_limit": 15,
        "duration_days": 30,
        "label": "Employer Pro",
        "owner_note": "TBD by owner",
        "published": False,
        "includes": (
            "A branded page, a higher post limit, and aggregated click totals for the page and roles. "
            "Counts only. No visitor identity."
        ),
    },
    {
        "id": "plan-featured",
        "plan_code": "featured",
        "amount_zar": None,
        "post_limit": None,
        "duration_days": 7,
        "label": "Featured listing",
        "owner_note": "TBD by owner",
        "published": False,
        "includes": (
            "A time-boxed Sponsored label on one approved opportunity. It is shown only when it matches "
            "the search, it is capped on each results page, and it does not change the order of other rows."
        ),
    },
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def audit(db: Session, *, actor_id: str | None, action: str, account_id: str | None,
          target_id: str | None, detail: str) -> None:
    db.add(EmployerAuditEvent(
        actor_user_id=actor_id,
        action=action[:40],
        account_id=account_id,
        target_id=target_id,
        detail=(detail or "")[:500],
    ))


def ensure_plans(db: Session, *, commit: bool = True) -> list[EmployerPlanConfig]:
    rows = db.query(EmployerPlanConfig).all()
    have = {row.plan_code for row in rows}
    added = False
    for spec in _PLAN_DEFAULTS:
        if spec["plan_code"] in have:
            continue
        added = True
        db.add(EmployerPlanConfig(
            id=spec["id"],
            plan_code=spec["plan_code"],
            amount_zar=spec["amount_zar"],
            currency="ZAR",
            post_limit=spec["post_limit"],
            duration_days=spec["duration_days"],
            label=spec["label"],
            owner_note=spec["owner_note"],
            published=spec["published"],
            includes=spec["includes"],
        ))
    if added:
        if commit:
            db.commit()
        else:
            db.flush()
    return db.query(EmployerPlanConfig).order_by(EmployerPlanConfig.plan_code.asc()).all()


def plan_by_code(db: Session, code: str) -> EmployerPlanConfig:
    ensure_plans(db, commit=False)
    row = db.query(EmployerPlanConfig).filter(EmployerPlanConfig.plan_code == code).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown plan.")
    return row


def price_is_public(plan: EmployerPlanConfig) -> bool:
    return bool(plan.published and plan.amount_zar is not None and plan.plan_code in PAID_PLAN_CODES)


def pricing_ready(plans: list[EmployerPlanConfig]) -> bool:
    paid = [plan for plan in plans if plan.plan_code in PAID_PLAN_CODES]
    return bool(paid) and all(price_is_public(plan) for plan in paid)


def public_plan(plan: EmployerPlanConfig) -> dict:
    if plan.plan_code == "free":
        price_status = "included"
        amount = 0
        note = plan.owner_note
    elif price_is_public(plan):
        price_status = "set"
        amount = plan.amount_zar
        note = plan.owner_note
    else:
        price_status = "tbd"
        amount = None
        note = "TBD by owner"
    return {
        "code": plan.plan_code,
        "label": plan.label,
        "currency": "ZAR",
        "amount_zar": amount,
        "price_status": price_status,
        "owner_note": note,
        "post_limit": plan.post_limit,
        "duration_days": plan.duration_days,
        "includes": plan.includes,
    }


def paystack_checkout_status() -> dict:
    """Employer checkout accepts a Paystack test secret only. Live keys stay off."""
    secret = (settings.PAYSTACK_SECRET_KEY or "").strip()
    public = (settings.PAYSTACK_PUBLIC_KEY or "").strip()
    if not secret and not public:
        return {
            "enabled": False,
            "mode": "off",
            "notice": (
                "Checkout is off. Add a Paystack test secret (sk_test_...) as PAYSTACK_SECRET_KEY "
                "and the matching public key as PAYSTACK_PUBLIC_KEY. No charge button is shown until then."
            ),
        }
    if secret.startswith("sk_live_") or public.startswith("pk_live_"):
        return {
            "enabled": False,
            "mode": "live_blocked",
            "notice": (
                "A live Paystack key is set. Employer checkout stays in test mode and is off "
                "until PAYSTACK_SECRET_KEY is a test secret (sk_test_...) and PAYSTACK_PUBLIC_KEY "
                "is a test public key (pk_test_...)."
            ),
        }
    if not secret.startswith("sk_test_") or not public.startswith("pk_test_"):
        return {
            "enabled": False,
            "mode": "invalid",
            "notice": (
                "Paystack keys are present but they are not a test pair (sk_test_ and pk_test_). "
                "Checkout is off."
            ),
        }
    return {
        "enabled": True,
        "mode": "test",
        "notice": "Paystack test mode is on. Cards are not stored here. A successful test payment is confirmed by the signed webhook.",
    }


def account_for_user(db: Session, user_id: str) -> EmployerAccount | None:
    return (
        db.query(EmployerAccount)
        .filter(EmployerAccount.user_id == user_id, EmployerAccount.deleted_at.is_(None))
        .one_or_none()
    )


def require_account(db: Session, user: User) -> EmployerAccount:
    account = account_for_user(db, user.id)
    if account is None:
        raise HTTPException(status_code=404, detail="Claim an employer page first.")
    return account


def require_verified(db: Session, user: User) -> EmployerAccount:
    account = require_account(db, user)
    if account.status != "verified":
        raise HTTPException(status_code=403, detail="This employer page is not verified yet.")
    return account


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _company_or_404(db: Session, company_id: str) -> Company:
    company = db.get(Company, company_id)
    if company is None or company.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Employer not found.")
    if not ((company.careers_url or "").strip() or (company.official_website or "").strip()):
        raise HTTPException(status_code=422, detail="This directory row has no site to match an email against.")
    return company


def start_claim(db: Session, user: User, company_id: str, work_email: str, *, admin_review: bool,
                note: str | None) -> tuple[EmployerAccount, str | None]:
    company = _company_or_404(db, company_id)
    email = work_email.strip().lower()
    existing = account_for_user(db, user.id)
    if existing is not None and existing.status == "verified":
        raise HTTPException(status_code=409, detail="This account already has a verified employer page.")
    taken = (
        db.query(EmployerAccount)
        .filter(
            EmployerAccount.company_id == company.id,
            EmployerAccount.status == "verified",
            EmployerAccount.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if taken is not None:
        raise HTTPException(status_code=409, detail="This employer page is already claimed.")
    matches = email_matches_company(email, company.careers_url, company.official_website)
    if admin_review:
        status_name = "pending_admin"
        method = None
        token = None
        token_hash = None
        expires = None
    else:
        if not matches:
            raise HTTPException(
                status_code=422,
                detail=(
                    "That email is not on this employer's own domain. "
                    "Use an address at the same domain as the careers page or the official website, "
                    "or ask for an administrator to check the claim."
                ),
            )
        status_name = "pending_email"
        method = None
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires = utcnow() + timedelta(hours=48)
    if existing is None:
        account = EmployerAccount(
            user_id=user.id,
            company_id=company.id,
            status=status_name,
            method=method,
            work_email=email,
            token_hash=token_hash,
            token_expires_at=expires,
            review_note=(note or "")[:500] or None,
        )
        db.add(account)
    else:
        account = existing
        account.company_id = company.id
        account.status = status_name
        account.method = method
        account.work_email = email
        account.token_hash = token_hash
        account.token_expires_at = expires
        account.review_note = (note or "")[:500] or None
        account.verified_at = None
        account.approved_by = None
    audit(
        db, actor_id=user.id, action="claim_admin" if admin_review else "claim_email",
        account_id=account.id, target_id=company.id,
        detail=f"status={status_name}",
    )
    db.commit()
    db.refresh(account)
    if token:
        _send_claim_email(email, token)
    return account, token if settings.ENV != "production" else None


def _send_claim_email(email: str, token: str) -> None:
    base = (settings.FRONTEND_URL or "https://sospana-sonke.vercel.app").rstrip("/")
    link = f"{base}/for-organisations/verify?token={token}"
    try:
        from app.notifications.email import get_email_provider
        get_email_provider().send(
            email,
            f"Confirm your {settings.APP_NAME} employer page",
            "Open this link to confirm the email is on your organisation's domain:\n"
            f"{link}\n\nThe link expires in 48 hours. "
            "If you did not ask for this, you can ignore it.",
        )
    except Exception:
        pass


def verify_claim_token(db: Session, token: str) -> EmployerAccount:
    digest = _hash_token(token.strip())
    account = (
        db.query(EmployerAccount)
        .filter(EmployerAccount.token_hash == digest, EmployerAccount.deleted_at.is_(None))
        .one_or_none()
    )
    if account is None or account.status != "pending_email":
        raise HTTPException(status_code=400, detail="This confirmation link is not valid.")
    expires = account.token_expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < utcnow():
            raise HTTPException(status_code=400, detail="This confirmation link has expired.")
    taken = (
        db.query(EmployerAccount)
        .filter(
            EmployerAccount.company_id == account.company_id,
            EmployerAccount.status == "verified",
            EmployerAccount.id != account.id,
            EmployerAccount.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if taken is not None:
        raise HTTPException(status_code=409, detail="This employer page is already claimed.")
    account.status = "verified"
    account.method = "domain_email"
    account.verified_at = utcnow()
    account.token_hash = None
    audit(db, actor_id=account.user_id, action="claim_verified", account_id=account.id,
          target_id=account.company_id, detail="method=domain_email")
    db.commit()
    db.refresh(account)
    return account


def decide_claim(db: Session, admin: User, account_id: str, *, approve: bool, note: str | None) -> EmployerAccount:
    account = db.get(EmployerAccount, account_id)
    if account is None or account.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    if account.status not in ("pending_admin", "pending_email"):
        raise HTTPException(status_code=409, detail="This claim is already decided.")
    if approve:
        taken = (
            db.query(EmployerAccount)
            .filter(
                EmployerAccount.company_id == account.company_id,
                EmployerAccount.status == "verified",
                EmployerAccount.id != account.id,
                EmployerAccount.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if taken is not None:
            raise HTTPException(status_code=409, detail="This employer page is already claimed.")
        account.status = "verified"
        account.method = "admin"
        account.verified_at = utcnow()
        account.approved_by = admin.id
        account.token_hash = None
        action = "claim_approved"
    else:
        account.status = "rejected"
        account.method = None
        action = "claim_rejected"
    account.review_note = (note or "")[:500] or account.review_note
    audit(db, actor_id=admin.id, action=action, account_id=account.id,
          target_id=account.company_id, detail=f"status={account.status}")
    db.commit()
    db.refresh(account)
    return account


def update_page(db: Session, user: User, *, blurb: str | None, contact_email: str | None,
                brand_headline: str | None) -> EmployerAccount:
    account = require_verified(db, user)
    if blurb is not None:
        account.public_blurb = blurb.strip()[:2000] or None
    if contact_email is not None:
        account.contact_email = contact_email.strip().lower()[:255] or None
    if brand_headline is not None:
        if not entitlement_live(db, account.id, "pro"):
            raise HTTPException(status_code=403, detail="A branded headline is part of Employer Pro.")
        account.brand_headline = brand_headline.strip()[:160] or None
    audit(db, actor_id=user.id, action="page_updated", account_id=account.id,
          target_id=account.company_id, detail="fields updated")
    db.commit()
    db.refresh(account)
    return account


def submit_correction(db: Session, user: User, field_name: str, proposed_value: str) -> EmployerCorrection:
    account = require_verified(db, user)
    if field_name not in CORRECTION_FIELDS:
        raise HTTPException(status_code=422, detail="You can propose a careers URL or an official website.")
    value = proposed_value.strip()
    if not value.lower().startswith("https://") or len(value) > 500:
        raise HTTPException(status_code=422, detail="Send an https link, up to 500 characters.")
    row = EmployerCorrection(
        account_id=account.id,
        company_id=account.company_id,
        field_name=field_name,
        proposed_value=value,
        status="pending",
    )
    db.add(row)
    audit(db, actor_id=user.id, action="correction_submitted", account_id=account.id,
          target_id=None, detail=f"field={field_name}")
    db.commit()
    db.refresh(row)
    return row


def decide_correction(db: Session, admin: User, correction_id: str, *, approve: bool, note: str | None) -> EmployerCorrection:
    row = db.get(EmployerCorrection, correction_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Correction not found.")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail="This correction is already decided.")
    company = db.get(Company, row.company_id)
    if approve:
        if company is None:
            raise HTTPException(status_code=404, detail="Employer not found.")
        if row.field_name == "careers_url":
            company.careers_url = row.proposed_value
        elif row.field_name == "official_website":
            company.official_website = row.proposed_value
        row.status = "approved"
    else:
        row.status = "rejected"
    row.reviewed_by = admin.id
    row.review_note = (note or "")[:500] or None
    audit(db, actor_id=admin.id, action="correction_" + row.status, account_id=row.account_id,
          target_id=row.id, detail=f"field={row.field_name}")
    db.commit()
    db.refresh(row)
    return row


def _post_limit(db: Session, account: EmployerAccount) -> int:
    code = "pro" if entitlement_live(db, account.id, "pro") else "free"
    plan = plan_by_code(db, code)
    return int(plan.post_limit or (15 if code == "pro" else 3))


def posts_used(db: Session, account_id: str) -> int:
    return (
        db.query(EmployerOpportunity)
        .filter(
            EmployerOpportunity.account_id == account_id,
            EmployerOpportunity.deleted_at.is_(None),
            EmployerOpportunity.status.in_(("pending", "approved")),
        )
        .count()
    )


def create_post(db: Session, user: User, payload: dict) -> EmployerOpportunity:
    account = require_verified(db, user)
    used = posts_used(db, account.id)
    limit = _post_limit(db, account)
    if used >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"This plan can have {limit} open or waiting posts. A rejected post does not count.",
        )
    company = db.get(Company, account.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Employer not found.")
    kind = (payload.get("opportunity_type") or "job").strip().lower().replace("-", "_").replace(" ", "_")
    if kind == "graduate_program":
        kind = "graduate_programme"
    if kind not in OPPORTUNITY_TYPES:
        raise HTTPException(status_code=422, detail="Unknown opportunity type.")
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    application_url = (payload.get("application_url") or "").strip()
    if len(title) < 3 or len(title) > 300:
        raise HTTPException(status_code=422, detail="Give the post a title.")
    if len(description) < 20:
        raise HTTPException(status_code=422, detail="Describe the opportunity in at least a short paragraph.")
    if not application_host_allowed(application_url, company.careers_url, company.official_website):
        raise HTTPException(
            status_code=422,
            detail="The application link has to be https on your own domain or on your own applicant system.",
        )
    closing = _future_date(payload.get("closing_date"))
    row = EmployerOpportunity(
        account_id=account.id,
        company_id=account.company_id,
        title=title,
        opportunity_type=kind,
        location=(payload.get("location") or "").strip()[:200] or None,
        country=company.country,
        description=description[:8000],
        application_url=application_url[:1000],
        closing_date=closing,
        field_of_study=(payload.get("field_of_study") or "").strip()[:400] or None,
        stipend_text=(payload.get("stipend_text") or "").strip()[:240] or None,
        status="pending",
        provenance="employer-submitted",
    )
    db.add(row)
    audit(db, actor_id=user.id, action="post_submitted", account_id=account.id,
          target_id=None, detail="status=pending")
    db.commit()
    db.refresh(row)
    return row


def _future_date(value) -> date | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    try:
        day = date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Closing date has to be YYYY-MM-DD.") from exc
    if day < utcnow().date():
        raise HTTPException(status_code=422, detail="A past closing date is left blank. Send a current date or omit it.")
    return day


def own_post(db: Session, account: EmployerAccount, post_id: str) -> EmployerOpportunity:
    row = db.get(EmployerOpportunity, post_id)
    if row is None or row.deleted_at is not None or row.account_id != account.id:
        raise HTTPException(status_code=404, detail="Post not found.")
    return row


def update_own_post(db: Session, user: User, post_id: str, payload: dict) -> EmployerOpportunity:
    account = require_verified(db, user)
    row = own_post(db, account, post_id)
    if row.status == "approved":
        raise HTTPException(status_code=409, detail="An approved post stays as it was checked. Submit a new one to change it.")
    if "title" in payload and payload["title"] is not None:
        title = str(payload["title"]).strip()
        if len(title) < 3:
            raise HTTPException(status_code=422, detail="Give the post a title.")
        row.title = title[:300]
    if "description" in payload and payload["description"] is not None:
        description = str(payload["description"]).strip()
        if len(description) < 20:
            raise HTTPException(status_code=422, detail="Describe the opportunity in at least a short paragraph.")
        row.description = description[:8000]
    if "application_url" in payload and payload["application_url"] is not None:
        company = db.get(Company, account.company_id)
        url = str(payload["application_url"]).strip()
        if company is None or not application_host_allowed(url, company.careers_url, company.official_website):
            raise HTTPException(
                status_code=422,
                detail="The application link has to be https on your own domain or on your own applicant system.",
            )
        row.application_url = url[:1000]
    row.status = "pending"
    row.rejection_note = None
    audit(db, actor_id=user.id, action="post_edited", account_id=account.id, target_id=row.id, detail="status=pending")
    db.commit()
    db.refresh(row)
    return row


def moderate_post(db: Session, admin: User, post_id: str, *, approve: bool, note: str | None) -> EmployerOpportunity:
    row = db.get(EmployerOpportunity, post_id)
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Post not found.")
    if row.status not in ("pending", "rejected", "approved"):
        raise HTTPException(status_code=409, detail="This post cannot be moderated.")
    row.reviewed_by = admin.id
    row.reviewed_at = utcnow()
    row.rejection_note = (note or "")[:500] or None
    if approve:
        vacancy = _publish_vacancy(db, row)
        row.vacancy_id = vacancy.id
        row.status = "approved"
        action = "post_approved"
    else:
        row.status = "rejected"
        if row.vacancy_id:
            vacancy = db.get(Vacancy, row.vacancy_id)
            if vacancy is not None:
                from app.services.opportunity_expiry import mark_expired
                vacancy.lifecycle_status = "REMOVED"
                mark_expired(vacancy)
        action = "post_rejected"
    audit(db, actor_id=admin.id, action=action, account_id=row.account_id,
          target_id=row.id, detail=f"status={row.status}")
    db.commit()
    db.refresh(row)
    return row


def _publish_vacancy(db: Session, row: EmployerOpportunity) -> Vacancy:
    now = utcnow()
    company = db.get(Company, row.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Employer not found.")
    source = (
        db.query(VacancySource)
        .filter(
            VacancySource.company_id == company.id,
            VacancySource.ats_type == EMPLOYER_ATS,
            VacancySource.deleted_at.is_(None),
        )
        .first()
    )
    if source is None:
        source = VacancySource(
            company_id=company.id,
            url=row.application_url,
            ats_type=EMPLOYER_ATS,
            active=False,
            robots_allowed=True,
            last_checked=now,
            last_status="ok",
        )
        db.add(source)
        db.flush()
    digest = hashlib.sha256(f"{row.id}|{row.title}|{row.application_url}".encode()).hexdigest()
    vacancy = db.get(Vacancy, row.vacancy_id) if row.vacancy_id else None
    if vacancy is None:
        vacancy = (
            db.query(Vacancy)
            .filter(Vacancy.external_id == f"employer-post:{row.id}", Vacancy.deleted_at.is_(None))
            .one_or_none()
        )
    if vacancy is None:
        vacancy = Vacancy(
            company_id=company.id,
            source_id=source.id,
            external_id=f"employer-post:{row.id}",
            title=row.title,
            opportunity_type=row.opportunity_type,
            content_hash=digest,
            first_seen_at=now,
            last_seen_at=now,
            is_open=True,
        )
        db.add(vacancy)
    vacancy.source_id = source.id
    vacancy.title = row.title
    vacancy.opportunity_type = row.opportunity_type
    vacancy.location = row.location
    vacancy.country = row.country or company.country
    vacancy.description = row.description
    vacancy.application_url = row.application_url
    vacancy.source_url = row.application_url
    vacancy.canonical_url = row.application_url
    vacancy.closing_date = row.closing_date
    vacancy.field_of_study = row.field_of_study
    vacancy.stipend_text = row.stipend_text
    vacancy.content_hash = digest
    vacancy.fingerprint = digest
    from app.services.opportunity_expiry import closing_has_passed, mark_active, mark_expired
    if closing_has_passed(vacancy.closing_date):
        mark_expired(vacancy, now)
    else:
        mark_active(vacancy)
    vacancy.verification_state = "DISCOVERED"
    vacancy.opportunity_reviewed = True
    vacancy.last_seen_at = now
    db.flush()
    return vacancy


def entitlement_live(db: Session, account_id: str, plan_code: str) -> bool:
    now = utcnow()
    rows = (
        db.query(EmployerEntitlement)
        .filter(
            EmployerEntitlement.account_id == account_id,
            EmployerEntitlement.plan_code == plan_code,
            EmployerEntitlement.deleted_at.is_(None),
            EmployerEntitlement.status == "active",
        )
        .all()
    )
    live = False
    for row in rows:
        ends = row.ends_at
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        if ends <= now:
            row.status = "expired"
            continue
        live = True
    return live


def click_totals(db: Session, user: User) -> dict:
    account = require_verified(db, user)
    if not entitlement_live(db, account.id, "pro"):
        raise HTTPException(status_code=403, detail="Aggregated click totals are part of Employer Pro.")
    company_clicks = (
        db.query(UsageClickDaily.clicks)
        .filter(UsageClickDaily.target_kind == "employer", UsageClickDaily.target_id == account.company_id)
        .all()
    )
    vacancy_ids = [
        row[0] for row in db.query(Vacancy.id).filter(Vacancy.company_id == account.company_id).all()
    ]
    role_rows = []
    if vacancy_ids:
        grouped = (
            db.query(UsageClickDaily.target_id, UsageClickDaily.clicks)
            .filter(UsageClickDaily.target_kind == "vacancy", UsageClickDaily.target_id.in_(vacancy_ids))
            .all()
        )
        totals: dict[str, int] = {}
        for target_id, clicks in grouped:
            totals[target_id] = totals.get(target_id, 0) + int(clicks or 0)
        titles = {
            row.id: row.title
            for row in db.query(Vacancy.id, Vacancy.title).filter(Vacancy.id.in_(list(totals))).all()
        } if totals else {}
        role_rows = [
            {"vacancy_id": vacancy_id, "title": titles.get(vacancy_id, ""), "clicks": clicks}
            for vacancy_id, clicks in sorted(totals.items())
        ]
    audit(db, actor_id=user.id, action="clicks_read", account_id=account.id,
          target_id=account.company_id, detail="aggregated")
    db.commit()
    return {
        "company_clicks": sum(int(row[0] or 0) for row in company_clicks),
        "roles": role_rows,
        "note": "Daily totals only. No IP address, no account id, and no question text.",
    }


def featured_matches(db: Session, filtered_query) -> list[tuple[Vacancy, Company, datetime]]:
    """Featured vacancies that already satisfy the caller's filters, capped, stable order."""
    now = utcnow()
    entitlements = (
        db.query(EmployerEntitlement)
        .filter(
            EmployerEntitlement.plan_code == "featured",
            EmployerEntitlement.status == "active",
            EmployerEntitlement.vacancy_id.isnot(None),
            EmployerEntitlement.deleted_at.is_(None),
            EmployerEntitlement.ends_at > now,
        )
        .order_by(EmployerEntitlement.starts_at.asc(), EmployerEntitlement.id.asc())
        .all()
    )
    if not entitlements:
        return []
    ids = [row.vacancy_id for row in entitlements if row.vacancy_id]
    from app.services.opportunity_expiry import is_publicly_listed, public_role_clauses
    matched = {
        vacancy.id: (vacancy, company)
        for vacancy, company in filtered_query.filter(Vacancy.id.in_(ids), *public_role_clauses()).all()
        if is_publicly_listed(vacancy)
    }
    chosen: list[tuple[Vacancy, Company, datetime]] = []
    for row in entitlements:
        pair = matched.get(row.vacancy_id or "")
        if pair is None:
            continue
        chosen.append((pair[0], pair[1], row.ends_at))
        if len(chosen) >= SPONSORED_CAP:
            break
    return chosen


def submitted_vacancy_ids(db: Session, vacancy_ids: list[str]) -> set[str]:
    if not vacancy_ids:
        return set()
    rows = (
        db.query(EmployerOpportunity.vacancy_id)
        .filter(
            EmployerOpportunity.vacancy_id.in_(vacancy_ids),
            EmployerOpportunity.status == "approved",
            EmployerOpportunity.deleted_at.is_(None),
        )
        .all()
    )
    return {row[0] for row in rows if row[0]}


def public_brand(db: Session, company_id: str) -> dict | None:
    account = (
        db.query(EmployerAccount)
        .filter(
            EmployerAccount.company_id == company_id,
            EmployerAccount.status == "verified",
            EmployerAccount.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if account is None:
        return None
    pro = entitlement_live(db, account.id, "pro")
    if not pro:
        return {"branded": False}
    return {
        "branded": True,
        "headline": account.brand_headline,
        "blurb": account.public_blurb,
        "contact_email": account.contact_email,
    }


def create_checkout(db: Session, user: User, plan_code: str, opportunity_id: str | None) -> dict:
    gate = paystack_checkout_status()
    if not gate["enabled"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=gate["notice"])
    if plan_code not in PAID_PLAN_CODES:
        raise HTTPException(status_code=422, detail="Choose Employer Pro or a featured listing.")
    plan = plan_by_code(db, plan_code)
    if not price_is_public(plan):
        raise HTTPException(status_code=409, detail="Pricing coming soon.")
    account = require_verified(db, user)
    vacancy_id = None
    if plan_code == "featured":
        if not opportunity_id:
            raise HTTPException(status_code=422, detail="Choose one approved opportunity to feature.")
        post = own_post(db, account, opportunity_id)
        if post.status != "approved" or not post.vacancy_id:
            raise HTTPException(status_code=409, detail="Only an approved opportunity can be featured.")
        vacancy_id = post.vacancy_id
        already = (
            db.query(EmployerEntitlement)
            .filter(
                EmployerEntitlement.vacancy_id == vacancy_id,
                EmployerEntitlement.plan_code == "featured",
                EmployerEntitlement.status == "active",
                EmployerEntitlement.ends_at > utcnow(),
                EmployerEntitlement.deleted_at.is_(None),
            )
            .first()
        )
        if already is not None:
            raise HTTPException(status_code=409, detail="This opportunity already has an active featured placement.")
    reference = "emp_" + uuid.uuid4().hex
    invoice = EmployerInvoice(
        account_id=account.id,
        plan_code=plan_code,
        amount_zar=int(plan.amount_zar or 0),
        currency="ZAR",
        provider="paystack",
        provider_reference=reference,
        status="pending",
        vacancy_id=vacancy_id,
        opportunity_id=opportunity_id,
    )
    db.add(invoice)
    audit(db, actor_id=user.id, action="checkout_started", account_id=account.id,
          target_id=None, detail=f"plan={plan_code}")
    db.commit()
    db.refresh(invoice)
    from app.payments.paystack import PaystackProvider
    callback = (settings.EMPLOYER_CHECKOUT_RETURN_URL or f"{settings.FRONTEND_URL.rstrip('/')}/organisation?checkout=return")
    try:
        session = PaystackProvider().start_checkout(
            email=user.email,
            amount_zar=invoice.amount_zar,
            reference=reference,
            metadata={
                "invoice_id": invoice.id,
                "account_id": account.id,
                "plan_code": plan_code,
                "purpose": "employer_plan",
            },
            callback_url=callback,
        )
    except Exception:
        invoice.status = "failed"
        audit(db, actor_id=user.id, action="checkout_failed", account_id=account.id,
              target_id=invoice.id, detail="provider_error")
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Paystack did not start a test checkout. Nothing was charged. Try again once the keys are valid.",
        )
    return {
        "authorization_url": session.authorization_url,
        "reference": session.reference,
        "invoice_id": invoice.id,
        "mode": "test",
    }


def _event_seen(db: Session, provider: str, reference: str, event_name: str) -> bool:
    return (
        db.query(EmployerPaymentEvent.id)
        .filter(
            EmployerPaymentEvent.provider == provider,
            EmployerPaymentEvent.provider_reference == reference,
            EmployerPaymentEvent.event_name == event_name,
        )
        .first()
        is not None
    )


def apply_provider_event(db: Session, *, event_name: str, reference: str | None, amount_zar: int | None,
                         provider_status: str | None) -> dict:
    """Grant or revoke from a signature-checked event. A repeat event changes nothing."""
    if not reference:
        return {"status": "ignored"}
    provider = "paystack"
    if _event_seen(db, provider, reference, event_name):
        return {"status": "duplicate"}
    invoice = (
        db.query(EmployerInvoice)
        .filter(EmployerInvoice.provider == provider, EmployerInvoice.provider_reference == reference)
        .one_or_none()
    )
    event = EmployerPaymentEvent(
        provider=provider,
        provider_reference=reference,
        event_name=event_name[:60],
        invoice_id=invoice.id if invoice else None,
        amount_zar=amount_zar,
        provider_status=(provider_status or "")[:40] or None,
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}
    if invoice is None:
        audit(db, actor_id=None, action="webhook_unknown", account_id=None, target_id=None,
              detail=f"event={event_name}")
        db.commit()
        return {"status": "unknown_reference"}
    if event_name == "charge.success":
        if amount_zar is None or int(amount_zar) != int(invoice.amount_zar):
            invoice.status = "failed"
            audit(db, actor_id=None, action="webhook_amount_mismatch", account_id=invoice.account_id,
                  target_id=invoice.id, detail="amount")
            db.commit()
            return {"status": "amount_mismatch"}
        if invoice.status != "paid":
            _grant_invoice(db, invoice)
        audit(db, actor_id=None, action="webhook_paid", account_id=invoice.account_id,
              target_id=invoice.id, detail=f"plan={invoice.plan_code}")
        db.commit()
        return {"status": "paid"}
    if event_name in ("refund.processed", "charge.refunded"):
        _refund_invoice(db, invoice)
        audit(db, actor_id=None, action="webhook_refunded", account_id=invoice.account_id,
              target_id=invoice.id, detail=f"plan={invoice.plan_code}")
        db.commit()
        return {"status": "refunded"}
    if event_name == "payment_failed":
        if invoice.status == "pending":
            invoice.status = "failed"
        audit(db, actor_id=None, action="webhook_failed", account_id=invoice.account_id,
              target_id=invoice.id, detail="failed")
        db.commit()
        return {"status": "failed"}
    db.commit()
    return {"status": "ignored"}


def _grant_invoice(db: Session, invoice: EmployerInvoice) -> EmployerEntitlement:
    now = utcnow()
    plan = plan_by_code(db, invoice.plan_code)
    days = int(plan.duration_days or (7 if invoice.plan_code == "featured" else 30))
    invoice.status = "paid"
    invoice.paid_at = now
    entitlement = EmployerEntitlement(
        account_id=invoice.account_id,
        plan_code=invoice.plan_code,
        status="active",
        starts_at=now,
        ends_at=now + timedelta(days=days),
        cancel_at_period_end=False,
        vacancy_id=invoice.vacancy_id,
        opportunity_id=invoice.opportunity_id,
        invoice_id=invoice.id,
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def _refund_invoice(db: Session, invoice: EmployerInvoice) -> None:
    now = utcnow()
    invoice.status = "refunded"
    invoice.refunded_at = now
    rows = (
        db.query(EmployerEntitlement)
        .filter(EmployerEntitlement.invoice_id == invoice.id, EmployerEntitlement.deleted_at.is_(None))
        .all()
    )
    for row in rows:
        row.status = "refunded"
        row.ends_at = now


def cancel_entitlement(db: Session, user: User, entitlement_id: str) -> EmployerEntitlement:
    account = require_verified(db, user)
    row = db.get(EmployerEntitlement, entitlement_id)
    if row is None or row.deleted_at is not None or row.account_id != account.id:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if row.status != "active":
        raise HTTPException(status_code=409, detail="This plan is not active.")
    row.cancel_at_period_end = True
    audit(db, actor_id=user.id, action="plan_cancel_requested", account_id=account.id,
          target_id=row.id, detail="access until period end")
    db.commit()
    db.refresh(row)
    return row


def request_refund(db: Session, user: User, invoice_id: str) -> EmployerInvoice:
    account = require_verified(db, user)
    invoice = db.get(EmployerInvoice, invoice_id)
    if invoice is None or invoice.account_id != account.id:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.status != "paid":
        raise HTTPException(status_code=409, detail="Only a paid invoice can be marked for a refund.")
    invoice.status = "refund_requested"
    audit(db, actor_id=user.id, action="refund_requested", account_id=account.id,
          target_id=invoice.id, detail="awaiting admin")
    db.commit()
    db.refresh(invoice)
    return invoice


def admin_refund(db: Session, admin: User, invoice_id: str) -> dict:
    gate = paystack_checkout_status()
    if not gate["enabled"]:
        raise HTTPException(status_code=503, detail=gate["notice"])
    invoice = db.get(EmployerInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.status not in ("paid", "refund_requested"):
        raise HTTPException(status_code=409, detail="This invoice is not waiting for a refund.")
    import httpx
    response = httpx.post(
        "https://api.paystack.co/refund",
        headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"},
        json={"transaction": invoice.provider_reference},
        timeout=30.0,
    )
    if response.status_code >= 400:
        audit(db, actor_id=admin.id, action="refund_provider_failed", account_id=invoice.account_id,
              target_id=invoice.id, detail=f"http={response.status_code}")
        db.commit()
        raise HTTPException(status_code=502, detail="Paystack did not accept the refund. The plan is unchanged.")
    _refund_invoice(db, invoice)
    if not _event_seen(db, "paystack", invoice.provider_reference, "refund.processed"):
        db.add(EmployerPaymentEvent(
            provider="paystack",
            provider_reference=invoice.provider_reference,
            event_name="refund.processed",
            invoice_id=invoice.id,
            amount_zar=invoice.amount_zar,
            provider_status="processed",
        ))
    audit(db, actor_id=admin.id, action="refund_sent", account_id=invoice.account_id,
          target_id=invoice.id, detail="provider=paystack")
    db.commit()
    return {"invoice_id": invoice.id, "status": "refunded"}


def revenue_summary(db: Session) -> dict:
    ensure_plans(db)
    invoices = db.query(EmployerInvoice).filter(EmployerInvoice.deleted_at.is_(None)).all()
    paid = sum(row.amount_zar for row in invoices if row.status == "paid")
    refunded = sum(row.amount_zar for row in invoices if row.status == "refunded")
    now = utcnow()
    entitlements = db.query(EmployerEntitlement).filter(EmployerEntitlement.deleted_at.is_(None)).all()
    active_pro = 0
    active_featured = 0
    featured = []
    for row in entitlements:
        ends = row.ends_at
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        live = row.status == "active" and ends > now
        if live and row.plan_code == "pro":
            active_pro += 1
        if row.plan_code == "featured":
            if live:
                active_featured += 1
            featured.append({
                "id": row.id,
                "account_id": row.account_id,
                "vacancy_id": row.vacancy_id,
                "status": "expired" if row.status == "active" and ends <= now else row.status,
                "starts_at": row.starts_at.isoformat(),
                "ends_at": row.ends_at.isoformat(),
                "cancel_at_period_end": row.cancel_at_period_end,
            })
    pending_claims = (
        db.query(EmployerAccount)
        .filter(EmployerAccount.status.in_(("pending_email", "pending_admin")), EmployerAccount.deleted_at.is_(None))
        .count()
    )
    pending_posts = (
        db.query(EmployerOpportunity)
        .filter(EmployerOpportunity.status == "pending", EmployerOpportunity.deleted_at.is_(None))
        .count()
    )
    gate = paystack_checkout_status()
    plans = [public_plan(plan) | {"published": plan.published, "amount_zar_raw": plan.amount_zar, "owner_note": plan.owner_note}
             for plan in db.query(EmployerPlanConfig).order_by(EmployerPlanConfig.plan_code.asc()).all()]
    return {
        "currency": "ZAR",
        "paid_zar": paid,
        "refunded_zar": refunded,
        "net_zar": paid,
        "active_pro": active_pro,
        "active_featured": active_featured,
        "pending_claims": pending_claims,
        "pending_posts": pending_posts,
        "featured_slots": featured,
        "plans": plans,
        "checkout": gate,
        "sponsored_cap": SPONSORED_CAP,
    }
