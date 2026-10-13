"""Organisation accounts, claims, posts, and Paystack test-mode checkout.

Candidates receive 403. One organisation cannot read or edit another's rows.
Checkout returns 503 when Paystack test keys are absent, and never a stand-in URL.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.routes_auth import CURRENT_POLICY_VERSION
from app.core.config import settings
from app.core.deps import get_current_user, require_admin
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.db.session import get_db
from app.models.organisation import (
    EmployerAccount,
    EmployerCorrection,
    EmployerEntitlement,
    EmployerInvoice,
    EmployerOpportunity,
    EmployerPlanConfig,
)
from app.models.user import User
from app.schemas.auth import RegisterResponse, UserResponse
from app.schemas.organisation import (
    AccountResponse,
    CheckoutRequest,
    ClaimRequest,
    CorrectionRequest,
    ModerationRequest,
    OpportunityPatchRequest,
    OpportunityWriteRequest,
    OrganisationRegisterRequest,
    PageUpdateRequest,
    PlanPriceUpdate,
    VerifyClaimRequest,
)
from app.services.employer_service import (
    SPONSORED_CAP,
    RANKING_NOTE,
    account_for_user,
    admin_refund,
    apply_provider_event,
    cancel_entitlement,
    click_totals,
    create_checkout,
    create_post,
    decide_claim,
    decide_correction,
    ensure_plans,
    moderate_post,
    paystack_checkout_status,
    plan_by_code,
    posts_used,
    pricing_ready,
    public_brand,
    public_plan,
    request_refund,
    require_verified,
    revenue_summary,
    start_claim,
    submit_correction,
    update_own_post,
    update_page,
    verify_claim_token,
    _post_limit,
)

router = APIRouter(prefix="/organisations", tags=["organisations"])
admin_router = APIRouter(prefix="/admin/organisations", tags=["organisations"])


def require_employer(user: User = Depends(get_current_user)) -> User:
    if user.role != "employer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation access required.")
    return user


def _account_out(account: EmployerAccount, token: str | None = None) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        company_id=account.company_id,
        status=account.status,
        method=account.method,
        work_email=account.work_email,
        verified_at=account.verified_at,
        public_blurb=account.public_blurb,
        contact_email=account.contact_email,
        brand_headline=account.brand_headline,
        verification_token=token,
    )


@router.get("/plans")
@limiter.limit("60/minute")
def list_plans(request: Request, db: Session = Depends(get_db)):
    plans = ensure_plans(db)
    ready = pricing_ready(plans)
    return {
        "currency": "ZAR",
        "pricing_ready": ready,
        "message": None if ready else "Pricing coming soon",
        "plans": [public_plan(plan) for plan in plans],
        "checkout": paystack_checkout_status(),
        "sponsored_cap": SPONSORED_CAP,
        "ranking_note": RANKING_NOTE,
        "seeker_note": "Search, alerts, and CV tools stay free for job seekers.",
    }


@router.get("/brand/{company_id}")
@limiter.limit("120/minute")
def brand(request: Request, company_id: str, db: Session = Depends(get_db)):
    profile = public_brand(db, company_id)
    if profile is None:
        return {"branded": False}
    return profile


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def register_organisation(request: Request, body: OrganisationRegisterRequest, db: Session = Depends(get_db)):
    if not body.accepted_policy:
        raise HTTPException(status_code=400, detail="Accept the privacy policy and the terms to create an organisation account.")
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    from datetime import datetime, timezone
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        role="employer",
        policy_accepted_at=datetime.now(timezone.utc),
        policy_version=CURRENT_POLICY_VERSION,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    from app.core import security
    token = security.create_email_verification_token(user.id)
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        email_verification_token=token if settings.ENV != "production" else None,
    )


@router.post("/claims", response_model=AccountResponse)
@limiter.limit("5/hour")
def claim_with_email(request: Request, body: ClaimRequest, db: Session = Depends(get_db),
                     user: User = Depends(require_employer)):
    account, token = start_claim(db, user, body.company_id, body.work_email, admin_review=False, note=body.note)
    return _account_out(account, token)


@router.post("/claims/admin", response_model=AccountResponse)
@limiter.limit("5/hour")
def claim_for_admin(request: Request, body: ClaimRequest, db: Session = Depends(get_db),
                    user: User = Depends(require_employer)):
    account, token = start_claim(db, user, body.company_id, body.work_email, admin_review=True, note=body.note)
    return _account_out(account, token)


@router.post("/claims/verify", response_model=AccountResponse)
@limiter.limit("10/hour")
def verify_claim(request: Request, body: VerifyClaimRequest, db: Session = Depends(get_db)):
    return _account_out(verify_claim_token(db, body.token))


@router.get("/me")
def my_account(db: Session = Depends(get_db), user: User = Depends(require_employer)):
    account = account_for_user(db, user.id)
    if account is None:
        return {"account": None, "post_limit": None, "posts_used": 0, "pro": False}
    from app.services.employer_service import entitlement_live
    limit = _post_limit(db, account) if account.status == "verified" else None
    return {
        "account": _account_out(account).model_dump(),
        "post_limit": limit,
        "posts_used": posts_used(db, account.id) if account.status == "verified" else 0,
        "pro": entitlement_live(db, account.id, "pro") if account.status == "verified" else False,
        "checkout": paystack_checkout_status(),
    }


@router.patch("/me", response_model=AccountResponse)
@limiter.limit("30/hour")
def patch_page(request: Request, body: PageUpdateRequest, db: Session = Depends(get_db),
               user: User = Depends(require_employer)):
    account = update_page(
        db, user,
        blurb=body.public_blurb,
        contact_email=str(body.contact_email) if body.contact_email else None,
        brand_headline=body.brand_headline,
    )
    return _account_out(account)


@router.post("/corrections")
@limiter.limit("10/hour")
def corrections(request: Request, body: CorrectionRequest, db: Session = Depends(get_db),
                user: User = Depends(require_employer)):
    row = submit_correction(db, user, body.field_name, body.proposed_value)
    return {"id": row.id, "status": row.status, "field_name": row.field_name}


@router.get("/opportunities")
def list_posts(db: Session = Depends(get_db), user: User = Depends(require_employer)):
    account = require_verified(db, user)
    rows = (
        db.query(EmployerOpportunity)
        .filter(EmployerOpportunity.account_id == account.id, EmployerOpportunity.deleted_at.is_(None))
        .order_by(EmployerOpportunity.created_at.desc())
        .all()
    )
    return [_post_out(row) for row in rows]


@router.post("/opportunities", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def post_opportunity(request: Request, body: OpportunityWriteRequest, db: Session = Depends(get_db),
                     user: User = Depends(require_employer)):
    row = create_post(db, user, body.model_dump())
    return _post_out(row)


@router.patch("/opportunities/{post_id}")
@limiter.limit("20/hour")
def patch_opportunity(request: Request, post_id: str, body: OpportunityPatchRequest, db: Session = Depends(get_db),
                      user: User = Depends(require_employer)):
    row = update_own_post(db, user, post_id, body.model_dump(exclude_unset=True))
    return _post_out(row)


@router.get("/clicks")
@limiter.limit("30/hour")
def clicks(request: Request, db: Session = Depends(get_db), user: User = Depends(require_employer)):
    return click_totals(db, user)


@router.post("/checkout")
@limiter.limit("10/hour")
def checkout(request: Request, body: CheckoutRequest, db: Session = Depends(get_db),
             user: User = Depends(require_employer)):
    return create_checkout(db, user, body.plan_code, body.opportunity_id)


@router.post("/entitlements/{entitlement_id}/cancel")
@limiter.limit("10/hour")
def cancel(request: Request, entitlement_id: str, db: Session = Depends(get_db),
           user: User = Depends(require_employer)):
    row = cancel_entitlement(db, user, entitlement_id)
    return {
        "id": row.id,
        "status": row.status,
        "cancel_at_period_end": row.cancel_at_period_end,
        "ends_at": row.ends_at.isoformat(),
    }


@router.post("/invoices/{invoice_id}/refund-request")
@limiter.limit("5/hour")
def refund_request(request: Request, invoice_id: str, db: Session = Depends(get_db),
                   user: User = Depends(require_employer)):
    invoice = request_refund(db, user, invoice_id)
    return {"id": invoice.id, "status": invoice.status}


@router.get("/invoices")
def invoices(db: Session = Depends(get_db), user: User = Depends(require_employer)):
    account = require_verified(db, user)
    rows = (
        db.query(EmployerInvoice)
        .filter(EmployerInvoice.account_id == account.id)
        .order_by(EmployerInvoice.created_at.desc())
        .all()
    )
    entitlements = (
        db.query(EmployerEntitlement)
        .filter(EmployerEntitlement.account_id == account.id, EmployerEntitlement.deleted_at.is_(None))
        .all()
    )
    return {
        "invoices": [_invoice_out(row) for row in rows],
        "entitlements": [
            {
                "id": row.id,
                "plan_code": row.plan_code,
                "status": row.status,
                "starts_at": row.starts_at.isoformat(),
                "ends_at": row.ends_at.isoformat(),
                "cancel_at_period_end": row.cancel_at_period_end,
                "vacancy_id": row.vacancy_id,
            }
            for row in entitlements
        ],
    }


@router.post("/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    gate = paystack_checkout_status()
    if not gate["enabled"]:
        raise HTTPException(status_code=503, detail=gate["notice"])
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature")
    from app.payments.paystack import PaystackProvider
    provider = PaystackProvider()
    if not provider.verify_webhook(raw, signature):
        raise HTTPException(status_code=401, detail="Webhook signature did not match.")
    try:
        body = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Webhook body was not JSON.")
    event_name = str(body.get("event") or "")
    data = body.get("data") or {}
    reference = data.get("reference") or (data.get("transaction") or {}).get("reference")
    amount = data.get("amount")
    amount_zar = int(amount) // 100 if isinstance(amount, (int, float)) and not isinstance(amount, bool) else None
    if event_name == "refund.processed":
        transaction = data.get("transaction") or {}
        reference = transaction.get("reference") or reference
        if amount_zar is None and isinstance(transaction.get("amount"), int):
            amount_zar = int(transaction["amount"]) // 100
    normalised = event_name
    if event_name == "charge.success":
        normalised = "charge.success"
    elif event_name in ("charge.failed",):
        normalised = "payment_failed"
    elif event_name in ("refund.processed",):
        normalised = "refund.processed"
    else:
        normalised = event_name or "ignored"
    result = apply_provider_event(
        db,
        event_name=normalised,
        reference=reference,
        amount_zar=amount_zar,
        provider_status=str(data.get("status") or "")[:40] or None,
    )
    return result


def _post_out(row: EmployerOpportunity) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "opportunity_type": row.opportunity_type,
        "status": row.status,
        "provenance": row.provenance,
        "application_url": row.application_url,
        "closing_date": row.closing_date.isoformat() if row.closing_date else None,
        "vacancy_id": row.vacancy_id,
        "location": row.location,
        "description": row.description,
        "rejection_note": row.rejection_note,
    }


def _invoice_out(row: EmployerInvoice) -> dict:
    return {
        "id": row.id,
        "plan_code": row.plan_code,
        "amount_zar": row.amount_zar,
        "currency": row.currency,
        "status": row.status,
        "provider": row.provider,
        "reference": row.provider_reference,
        "paid_at": row.paid_at.isoformat() if row.paid_at else None,
        "refunded_at": row.refunded_at.isoformat() if row.refunded_at else None,
    }


@admin_router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return revenue_summary(db)


@admin_router.get("/claims")
def list_claims(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = (
        db.query(EmployerAccount)
        .filter(EmployerAccount.deleted_at.is_(None))
        .order_by(EmployerAccount.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "company_id": row.company_id,
            "status": row.status,
            "method": row.method,
            "work_email": row.work_email,
            "review_note": row.review_note,
        }
        for row in rows
    ]


@admin_router.post("/claims/{account_id}")
def moderate_claim(account_id: str, body: ModerationRequest, db: Session = Depends(get_db),
                   admin: User = Depends(require_admin)):
    account = decide_claim(db, admin, account_id, approve=body.approve, note=body.note)
    return _account_out(account)


@admin_router.get("/posts")
def list_moderation(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = (
        db.query(EmployerOpportunity)
        .filter(EmployerOpportunity.deleted_at.is_(None))
        .order_by(EmployerOpportunity.created_at.desc())
        .limit(200)
        .all()
    )
    return [_post_out(row) | {"account_id": row.account_id, "company_id": row.company_id} for row in rows]


@admin_router.post("/posts/{post_id}")
def moderate(post_id: str, body: ModerationRequest, db: Session = Depends(get_db),
             admin: User = Depends(require_admin)):
    row = moderate_post(db, admin, post_id, approve=body.approve, note=body.note)
    return _post_out(row)


@admin_router.get("/corrections")
def list_corrections(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = (
        db.query(EmployerCorrection)
        .filter(EmployerCorrection.deleted_at.is_(None))
        .order_by(EmployerCorrection.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": row.id,
            "account_id": row.account_id,
            "company_id": row.company_id,
            "field_name": row.field_name,
            "proposed_value": row.proposed_value,
            "status": row.status,
        }
        for row in rows
    ]


@admin_router.post("/corrections/{correction_id}")
def moderate_correction(correction_id: str, body: ModerationRequest, db: Session = Depends(get_db),
                        admin: User = Depends(require_admin)):
    row = decide_correction(db, admin, correction_id, approve=body.approve, note=body.note)
    return {"id": row.id, "status": row.status, "field_name": row.field_name}


@admin_router.patch("/plans/{plan_code}")
def update_plan(plan_code: str, body: PlanPriceUpdate, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    plan = plan_by_code(db, plan_code)
    if body.clear_amount:
        plan.amount_zar = None
        plan.published = False
        plan.owner_note = "TBD by owner"
    elif body.amount_zar is not None:
        if plan.plan_code == "free":
            plan.amount_zar = 0
            plan.owner_note = "Included. No charge."
        else:
            plan.amount_zar = body.amount_zar
            plan.owner_note = "Set by owner"
    if body.published is not None:
        if body.published and plan.plan_code != "free" and plan.amount_zar is None:
            raise HTTPException(status_code=422, detail="Set a ZAR amount before publishing a price.")
        plan.published = body.published
    if body.post_limit is not None:
        plan.post_limit = body.post_limit
    if body.duration_days is not None:
        plan.duration_days = body.duration_days
    from app.services.employer_service import audit
    audit(db, actor_id=admin.id, action="plan_price_updated", account_id=None, target_id=plan.id,
          detail=f"code={plan.plan_code} published={plan.published}")
    db.commit()
    return public_plan(plan) | {"published": plan.published}


@admin_router.post("/invoices/{invoice_id}/refund")
def refund(invoice_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_refund(db, admin, invoice_id)
