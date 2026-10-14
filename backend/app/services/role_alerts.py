"""Validate, store, and match saved daily-role alerts.

A saved alert is an explicit opt-in. Creating or editing one turns that row
on. The daily digest is the only email, and it stays quiet when nothing new
matches. Unsubscribe pauses every active row; it does not delete them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, defer

from app.models.company import Company
from app.models.role_alert import RoleAlert
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.category_groups import canonical_type, stored_values_for
from app.services.country_names import canonical_country, is_country, spellings_for
from app.services.opportunity_expiry import public_role_clauses, sa_today
from app.services.opportunity_type import OPPORTUNITY_TYPES

MAX_ALERTS = 8
OPEN_SAMPLE = 20
ALERT_CATEGORIES = frozenset({
    "SOE", "MUNI", "DEPT", "PRIVATE", "NGO", "UNI", "COLLEGE",
    "HOSPITAL", "SETA", "JSE", "SPORT", "FED", "MUSIC",
})
_KEYWORD_EXTRA = set(" &./,-")


def _blank(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _keyword_ok(value: str) -> bool:
    if len(value) < 2 or len(value) > 80:
        return False
    if any(ch in value for ch in "%_"):
        return False
    return all(ch.isalnum() or ch in _KEYWORD_EXTRA for ch in value)


def _normalise(db: Session, body_country, body_category, body_keyword, body_type) -> tuple[str | None, str | None, str | None, str | None]:
    country = _blank(body_country)
    category = _blank(body_category)
    keyword = _blank(body_keyword)
    kind = _blank(body_type)
    if country:
        canon = canonical_country(country)
        if not is_country(canon):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Choose a country from the directory.")
        names = spellings_for(canon)
        known = (db.query(Company.id)
                 .filter(Company.deleted_at.is_(None), Company.country.in_(names))
                 .first())
        if known is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Choose a country from the directory.")
        country = canon
    if category:
        code = canonical_type(category)
        if code not in ALERT_CATEGORIES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Choose a category from the list.")
        category = code
    if keyword:
        keyword = " ".join(keyword.split())
        if not _keyword_ok(keyword):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Use 2 to 80 letters or numbers. The characters % and _ are not allowed.",
            )
    if kind:
        kind = kind.lower().replace("-", "_").replace(" ", "_")
        if kind == "graduate_program":
            kind = "graduate_programme"
        if kind not in OPPORTUNITY_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Choose a type from the list.")
    if not country and not category and not keyword and not kind:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Choose a country, a category, a keyword, or a type.")
    return country, category, keyword, kind


def _same(row: RoleAlert, country, category, keyword, kind) -> bool:
    return (
        row.country == country and row.category == category
        and row.keyword == keyword and row.opportunity_type == kind
    )


def list_alerts(db: Session, user_id: str) -> list[RoleAlert]:
    return (db.query(RoleAlert)
            .filter(RoleAlert.user_id == user_id, RoleAlert.deleted_at.is_(None))
            .order_by(RoleAlert.created_at.desc(), RoleAlert.id)
            .all())


def active_alerts(db: Session, user_id: str) -> list[RoleAlert]:
    return [row for row in list_alerts(db, user_id) if row.active]


def create_alert(db: Session, user: User, *, country, category, keyword, opportunity_type=None) -> RoleAlert:
    country, category, keyword, kind = _normalise(db, country, category, keyword, opportunity_type)
    rows = list_alerts(db, user.id)
    for row in rows:
        if _same(row, country, category, keyword, kind):
            row.active = True
            db.commit()
            db.refresh(row)
            return row
    if len(rows) >= MAX_ALERTS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="You can save up to 8 alerts. Delete one to add another.")
    row = RoleAlert(
        user_id=user.id, country=country, category=category, keyword=keyword,
        opportunity_type=kind, active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_alert(db: Session, user: User, alert_id: str, *, country, category, keyword, opportunity_type=None) -> RoleAlert:
    row = db.get(RoleAlert, alert_id)
    if row is None or row.user_id != user.id or row.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    country, category, keyword, kind = _normalise(db, country, category, keyword, opportunity_type)
    for other in list_alerts(db, user.id):
        if other.id != row.id and _same(other, country, category, keyword, kind):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="You already saved this alert.")
    row.country, row.category, row.keyword, row.opportunity_type = country, category, keyword, kind
    row.active = True
    db.commit()
    db.refresh(row)
    return row


def delete_alert(db: Session, user_id: str, alert_id: str) -> None:
    row = db.get(RoleAlert, alert_id)
    if row is None or row.user_id != user_id or row.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    row.active = False
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()


def pause_all(db: Session, user_id: str) -> None:
    """One-click unsubscribe. Active stays the opt-in flag; updated_at is not."""
    for row in active_alerts(db, user_id):
        row.active = False


def alert_matches(alert: RoleAlert, vacancy: Vacancy, company: Company) -> bool:
    """Every field the person set must agree. An empty field means any."""
    if alert.country:
        place = canonical_country(vacancy.country or company.country or "")
        if place != canonical_country(alert.country):
            return False
    if alert.category:
        if canonical_type(company.source_type) != alert.category:
            return False
    if alert.keyword and alert.keyword.casefold() not in (vacancy.title or "").casefold():
        return False
    if alert.opportunity_type and (vacancy.opportunity_type or "job") != alert.opportunity_type:
        return False
    return bool(alert.country or alert.category or alert.keyword or alert.opportunity_type)


def _like(keyword: str) -> str:
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.casefold()}%"


def _alert_clause(alert: RoleAlert):
    parts = []
    if alert.country:
        names = spellings_for(alert.country)
        parts.append(func.coalesce(Vacancy.country, Company.country).in_(names))
    if alert.category:
        values = stored_values_for(alert.category) or (alert.category,)
        parts.append(func.upper(func.coalesce(Company.source_type, "")).in_(tuple(values)))
    if alert.keyword:
        parts.append(func.lower(Vacancy.title).like(_like(alert.keyword), escape="\\"))
    if alert.opportunity_type:
        parts.append(Vacancy.opportunity_type == alert.opportunity_type)
    return and_(*parts) if parts else None


def open_matches(db: Session, alerts: list[RoleAlert], *, limit: int = OPEN_SAMPLE) -> list[tuple[Vacancy, Company]]:
    """Currently open stored roles that match any alert, newest last-seen first.

    This sample is wider than the daily email, which only includes roles first
    seen in the last 24 hours. Callers label the two lists separately.
    """
    clauses = [c for c in (_alert_clause(a) for a in alerts if a.active and a.deleted_at is None) if c is not None]
    if not clauses:
        return []
    return (db.query(Vacancy, Company)
            .options(
                defer(Vacancy.description), defer(Vacancy.raw_content),
                defer(Vacancy.requirements_text), defer(Vacancy.qualifications),
                defer(Vacancy.experience), defer(Company.notes),
            )
            .join(Company, Company.id == Vacancy.company_id)
            .filter(
                Company.deleted_at.is_(None),
                Vacancy.duplicate_of_id.is_(None),
                *public_role_clauses(sa_today()),
                or_(*clauses),
            )
            .order_by(Vacancy.last_seen_at.desc(), Vacancy.title)
            .limit(limit)
            .all())


def link_for(vacancy: Vacancy, company: Company) -> str | None:
    for candidate in (vacancy.application_url, vacancy.source_url, company.careers_url):
        text = (candidate or "").strip()
        if text.lower().startswith(("http://", "https://")):
            return text
    return None


def seen_day(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.date().isoformat()


def preview(db: Session, user: User, *, now: datetime | None = None) -> dict:
    """What the next digest would list for this account. Sends nothing."""
    from app.services.daily_digest import MAX_WINDOW_HOURS, build_content

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    since = now - timedelta(hours=MAX_WINDOW_HOURS)
    alerts = active_alerts(db, user.id)
    content = build_content(db, user, since=since, until=now) if alerts else None

    def pack(title, employer, country, url, last_seen) -> dict:
        return {
            "title": title, "employer": employer, "country": country or "",
            "url": url, "last_seen": last_seen,
        }

    would = [
        pack(item.title, item.employer, item.country, item.url, item.last_seen or None)
        for item in (content.openings if content else [])
    ]
    sample = [
        pack(vac.title, comp.company_name, vac.country or comp.country or "",
             link_for(vac, comp), seen_day(vac.last_seen_at))
        for vac, comp in open_matches(db, alerts)
    ]
    return {
        "email_sent": False,
        "would_send": bool(would) and bool(
            user.email_verified and user.is_active and user.deleted_at is None and alerts
        ),
        "cadence": "One email a day. If nothing new matches, no email is sent.",
        "window_hours": MAX_WINDOW_HOURS,
        "digest_eligible": bool(user.email_verified and user.is_active and user.deleted_at is None),
        "would_email": would,
        "open_matches": sample,
    }
