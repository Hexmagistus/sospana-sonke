"""The daily digest: ONE email per opted-in user per day, "Your daily updates".

Every opportunity, alert and job-match notice is stored for the dashboard but is
never emailed on its own (see DIGEST_ONLY_TYPES in notification_service). This
module collects them, and the real new openings from the last 24 hours, into a
single morning email. Cron: ``POST /api/v1/cron/run/send_daily_digest`` at
06:00 UTC = 08:00 SAST (X-Cron-Secret header, same as every other job).

Rules, all enforced here and covered by tests:

* Idempotent. A ``digest_log`` row (UNIQUE user + SAST calendar day) is inserted
  *before* the send. A second call the same day finds the claim and skips.
* No empty emails. A user with nothing new in the window is skipped, no claim.
* POPIA / opt-in. Verified email, active, not deleted, and an explicit yes:
  opportunity alerts (openings and matches), tagging (admin-tagged posts) or an
  active page watch (page-changed notices). Each section follows its own yes. A
  user who used the digest's unsubscribe link stays off until they choose again.
* Safety. Global cap ``DIGEST_DAILY_SEND_CAP`` (default 250) over a rolling 24h
  that also counts notification and preference mail. ``DIGEST_DRY_RUN`` reports
  what would go out and sends / records nothing. Stops at the first provider
  failure (quota / auth) instead of hammering the API.
* Content is real data: vacancies first seen in the window that are still open,
  with the vacancy's own apply/source link or else the employer's careers link.
  Longest email: ``DIGEST_MAX_ITEMS`` items (default 25) plus a "see more" link.
* Order: South Africa, rest of SADC, rest of Africa, then other regions.

Verification, password-reset and other account mail stay immediate and are not
touched by this module.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.models.company import Company
from app.models.digest import DigestLog
from app.models.match import CandidateMatch
from app.models.notification import Notification
from app.models.profile import CandidateProfile
from app.models.user import User
from app.models.vacancy import Vacancy
from app.models.watch import CompanyWatch
from app.notifications.email import get_email_provider

logger = logging.getLogger(__name__)

SAST = timezone(timedelta(hours=2))
SUBJECT_TITLE = "Your daily updates"
UNSUBSCRIBE_TOKEN_TYPE = "digest_unsubscribe"
UNSUBSCRIBE_TOKEN_DAYS = 365
BAND_LABELS = {0: "South Africa", 1: "Rest of SADC", 2: "Rest of Africa", 3: "Other regions"}
# Hard ceiling for one run. A single request must not run past the cron caller's timeout.
MAX_USERS_PER_RUN = 400
# Wall-clock budget for one call. Whoever is left is picked up by the next call the
# same day (idempotent), so a slow provider cannot run a request past the caller's timeout.
MAX_RUN_SECONDS = 90.0

# Words that mark a role as one kind of post. A vacancy with no signal is kept (we
# cannot say it does not match); a vacancy that clearly names other kinds is dropped.
_POST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "permanent": ("permanent", "full-time", "full time"),
    "contract": ("contract", "fixed term", "fixed-term", "temporary", "temp "),
    "part_time": ("part-time", "part time"),
    "internship": ("intern", "work experience", "vacation work", "work integrated"),
    "learnership": ("learnership", "apprentice"),
    "graduate": ("graduate", "trainee"),
}


# ---------------------------------------------------------------- helpers

def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def digest_day(now: datetime) -> str:
    """The calendar day the digest belongs to, in South Africa time."""
    return _aware(now).astimezone(SAST).date().isoformat()


def _app_url() -> str:
    from app.services.preference_mail import public_app_url
    return public_app_url()


def unsubscribe_url(user_id: str) -> str:
    token = security._create_token(
        user_id, UNSUBSCRIBE_TOKEN_TYPE, timedelta(days=UNSUBSCRIBE_TOKEN_DAYS)
    )
    base = f"{settings.PUBLIC_API_URL.rstrip('/')}{settings.API_V1_PREFIX}"
    return f"{base}/notifications/digest/unsubscribe?token={token}"


def _valid_email(email: str | None) -> bool:
    e = (email or "").strip()
    return len(e) > 3 and "@" in e


def _tagging_yes(user: User) -> bool:
    return bool(user.allow_tagging and user.allow_tagging_chosen_at)


def _alerts_yes(user: User) -> bool:
    return bool(user.notify_opportunity_alerts)


def _resubscribed(user: User) -> bool:
    """True when the person chose alerts or tagging again after unsubscribing."""
    gone = _aware(user.digest_unsubscribed_at)
    if gone is None:
        return True
    later = [_aware(t) for t in (user.notify_opportunity_alerts_chosen_at,
                                 user.allow_tagging_chosen_at) if t is not None]
    return any(t > gone for t in later)


# ---------------------------------------------------------------- content

@dataclass
class Item:
    title: str
    employer: str
    url: str | None
    band: int = 3
    country: str = ""
    place: str = ""
    note: str = ""


@dataclass
class DigestContent:
    tagged: list[Item] = field(default_factory=list)
    watched: list[Item] = field(default_factory=list)
    agent: list[Item] = field(default_factory=list)
    matches: list[Item] = field(default_factory=list)
    openings: list[Item] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (len(self.tagged) + len(self.watched) + len(self.agent)
                + len(self.matches) + len(self.openings))


def _kinds_in(text: str) -> set[str]:
    low = f" {text.lower()} "
    return {k for k, words in _POST_KEYWORDS.items() if any(w in low for w in words)}


def _post_type_ok(preferred: str | None, vacancy: Vacancy) -> bool:
    if not preferred or preferred == "any":
        return True
    if preferred == "none":
        return False
    kinds = _kinds_in(f"{vacancy.title or ''} {vacancy.employment_type or ''}")
    return not kinds or preferred in kinds


def _link_for(vacancy: Vacancy, company: Company) -> str | None:
    for candidate in (vacancy.application_url, vacancy.source_url, company.careers_url):
        c = (candidate or "").strip()
        if c.lower().startswith(("http://", "https://")):
            return c
    return None


def _band(country: str | None) -> int:
    from app.services.scan_runner import country_band
    return country_band(country)


def _open_vacancy_rows(db: Session, since: datetime, until: datetime):
    return (db.query(Vacancy, Company)
            .join(Company, Company.id == Vacancy.company_id)
            .filter(Vacancy.deleted_at.is_(None), Company.deleted_at.is_(None),
                    Vacancy.is_open.is_(True), Vacancy.duplicate_of_id.is_(None),
                    or_(Vacancy.lifecycle_status.is_(None), Vacancy.lifecycle_status == "ACTIVE"),
                    Vacancy.first_seen_at > since, Vacancy.first_seen_at <= until))


def _scope(db: Session, user: User, profile: CandidateProfile | None):
    """(countries or None for everywhere, extra company ids, watch (country, type) pairs)."""
    watches = (db.query(CompanyWatch)
               .filter(CompanyWatch.user_id == user.id, CompanyWatch.active.is_(True)).all())
    countries: set[str] = set()
    if profile and (profile.country or "").strip():
        countries.add(profile.country.strip())
    everywhere = bool(profile and profile.willing_to_relocate) or not countries
    company_ids = {w.company_id for w in watches if w.company_id}
    pairs = [(w.country, (w.source_type or "").upper() or None)
             for w in watches if not w.company_id]
    return (None if everywhere else countries), company_ids, pairs


def _watch_pair_ok(pairs, company: Company) -> bool:
    for country, source_type in pairs:
        if country and country != company.country:
            continue
        if source_type and source_type != (company.source_type or "").upper():
            continue
        return True
    return False


def build_content(db: Session, user: User, *, since: datetime, until: datetime) -> DigestContent:
    """Everything this user may be emailed about in [since, until]. No caps here."""
    content = DigestContent()
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()

    if _tagging_yes(user):
        notes = (db.query(Notification)
                 .filter(Notification.user_id == user.id, Notification.type == "admin_suggestion",
                         Notification.created_at > since, Notification.created_at <= until)
                 .order_by(Notification.created_at.desc()).all())
        for n in notes:
            employer = ""
            for line in (n.body or "").split("\n"):
                if line.startswith("Employer: "):
                    employer = line[len("Employer: "):].strip()
            content.tagged.append(Item(title=n.title, employer=employer, url=n.link_url))

    # Page-change notices exist only because the person created a watch (explicit opt-in).
    for n in (db.query(Notification)
              .filter(Notification.user_id == user.id, Notification.type == "link_updated",
                      Notification.created_at > since, Notification.created_at <= until)
              .order_by(Notification.created_at.desc()).all()):
        content.watched.append(Item(title=n.title, employer="", url=n.link_url))

    if _alerts_yes(user):
        for n in (db.query(Notification)
                  .filter(Notification.user_id == user.id, Notification.type == "daily_agent_briefing",
                          Notification.created_at > since, Notification.created_at <= until)
                  .order_by(Notification.created_at.desc()).all()):
            content.agent.append(Item(title=n.title, employer="", url=f"{_app_url()}/agent"))
        seen: set[str] = set()
        preferred = user.preferred_post_type if user.preferred_post_state == "chosen" else None
        if preferred != "none":
            for m, vac, comp in (db.query(CandidateMatch, Vacancy, Company)
                                 .join(Vacancy, Vacancy.id == CandidateMatch.vacancy_id)
                                 .join(Company, Company.id == Vacancy.company_id)
                                 .filter(CandidateMatch.user_id == user.id,
                                         CandidateMatch.band.in_(("Strong", "Good")),
                                         CandidateMatch.created_at > since,
                                         CandidateMatch.created_at <= until,
                                         Vacancy.deleted_at.is_(None), Vacancy.is_open.is_(True),
                                         Company.deleted_at.is_(None))
                                 .order_by(CandidateMatch.score.desc()).all()):
                if vac.id in seen:
                    continue
                seen.add(vac.id)
                country = vac.country or comp.country or ""
                content.matches.append(Item(
                    title=vac.title, employer=comp.company_name, url=_link_for(vac, comp),
                    band=_band(country), country=country, place=vac.city or vac.location or "",
                    note=f"{int(m.score)}% match",
                ))
            countries, company_ids, pairs = _scope(db, user, profile)
            for vac, comp in _open_vacancy_rows(db, since, until).all():
                if vac.id in seen:
                    continue
                country = vac.country or comp.country or ""
                in_country = countries is None or country in countries
                watched = comp.id in company_ids or _watch_pair_ok(pairs, comp)
                if not (in_country or watched):
                    continue
                if not _post_type_ok(preferred, vac):
                    continue
                seen.add(vac.id)
                content.openings.append(Item(
                    title=vac.title, employer=comp.company_name, url=_link_for(vac, comp),
                    band=_band(country), country=country, place=vac.city or vac.location or "",
                ))

    for group in (content.matches, content.openings):
        group.sort(key=lambda i: (i.band, i.country, i.employer.lower(), i.title.lower()))
    return content


# ---------------------------------------------------------------- rendering

def _line(item: Item) -> list[str]:
    head = f"- {item.title}"
    if item.employer:
        head += f" at {item.employer}"
    tail = ", ".join(x for x in (item.place, item.note) if x)
    if tail:
        head += f" ({tail})"
    out = [head]
    if item.url:
        out.append(item.url)
    return out


def render_digest(user: User, content: DigestContent, *, now: datetime, max_items: int,
                  window_hours: int = 24) -> tuple[str, str, int]:
    """(subject, body, items_listed). Section order is fixed; the cap is global."""
    budget = max(1, int(max_items))
    total = content.total
    first = (user.first_name or "").strip()
    day = _aware(now).astimezone(SAST)
    lines = [
        SUBJECT_TITLE,
        "",
        f"Hello {first}," if first else "Hello,",
        "",
        f"Here is what is new for you in the last {window_hours} hours: "
        f"{total} item{'s' if total != 1 else ''}.",
        "",
    ]
    listed = 0

    def section(heading: str, items: list[Item]) -> None:
        nonlocal listed
        take = items[: max(0, budget - listed)]
        if not take:
            return
        lines.extend([heading.upper(), ""])
        for it in take:
            lines.extend(_line(it))
        lines.append("")
        listed += len(take)

    section("Tagged for you by our team", content.tagged)
    section("Careers pages you are watching have changed", content.watched)
    section("Prepared by your daily agent", content.agent)
    section("Strong matches for your profile", content.matches)
    # Openings grouped by region band, South Africa first.
    for band in (0, 1, 2, 3):
        section(f"New openings: {BAND_LABELS[band]}", [i for i in content.openings if i.band == band])

    more = total - listed
    if more > 0:
        lines.extend([f"...and {more} more. See them all in the app:", f"{_app_url()}/agent", ""])
    lines.extend([
        "Why you are receiving this: you have a Sospana Sonke account and chose to get "
        "opportunity updates. We send one email a day, never more.",
        "",
        "Change what you receive:",
        f"{_app_url()}/preferences",
        "",
        "Unsubscribe from the daily updates with one click:",
        unsubscribe_url(user.id),
        "",
        "Privacy Policy:",
        f"{_app_url()}/privacy",
    ])
    subject = f"{SUBJECT_TITLE}: {total} new for you ({day:%d %b})"
    return subject, "\n".join(lines), listed


# ---------------------------------------------------------------- run

def _emails_used_24h(db: Session, now: datetime) -> int:
    """Everything the app sent in the last 24h: digests, notification mail, preference notices."""
    start = now - timedelta(hours=24)
    digests = (db.query(func.count(DigestLog.id))
               .filter(DigestLog.status == "sent", DigestLog.sent_at >= start).scalar() or 0)
    notes = (db.query(func.count(Notification.id))
             .filter(Notification.email_sent.is_(True), Notification.created_at >= start).scalar() or 0)
    prompts = (db.query(func.count(User.id))
               .filter(User.consent_prompt_sent_at.isnot(None),
                       User.consent_prompt_sent_at >= start).scalar() or 0)
    return int(digests) + int(notes) + int(prompts)


def _candidates(db: Session, day: str) -> list[User]:
    """Verified, active candidates with no digest claimed yet today. Consent is checked per user."""
    already = db.query(DigestLog.user_id).filter(DigestLog.digest_date == day)
    users = (db.query(User)
             .filter(User.role == "candidate", User.is_active.is_(True), User.deleted_at.is_(None),
                     User.email_verified.is_(True), User.id.notin_(already))
             .all())
    return [u for u in users if _valid_email(u.email)]


def _may_receive(db: Session, user: User) -> bool:
    if not _resubscribed(user):
        return False
    if _alerts_yes(user) or _tagging_yes(user):
        return True
    return db.query(CompanyWatch.id).filter(CompanyWatch.user_id == user.id,
                                            CompanyWatch.active.is_(True)).first() is not None


def _sort_users(db: Session, users: list[User]) -> list[User]:
    """South Africa first, then SADC, Africa, elsewhere (profile country); oldest account first."""
    countries = {uid: c for uid, c in db.query(CandidateProfile.user_id, CandidateProfile.country).all()}
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(users, key=lambda u: (_band(countries.get(u.id)), _aware(u.created_at) or epoch, u.id))


def _previous_window_end(db: Session, user_id: str, now: datetime) -> datetime | None:
    row = (db.query(DigestLog.window_end)
           .filter(DigestLog.user_id == user_id, DigestLog.status == "sent",
                   DigestLog.window_end.isnot(None))
           .order_by(DigestLog.window_end.desc()).first())
    end = _aware(row[0]) if row else None
    if end is None or now - end > timedelta(hours=48):
        return None
    return end


def run_daily_digest(db: Session, *, now: datetime | None = None, dry_run: bool | None = None,
                     provider=None) -> dict:
    """Send (or, in dry-run, only count) today's digests. Safe to call any number of times a day."""
    now = _aware(now) if now else datetime.now(timezone.utc)
    dry = settings.DIGEST_DRY_RUN if dry_run is None else bool(dry_run)
    cap = max(0, int(settings.DIGEST_DAILY_SEND_CAP))
    day = digest_day(now)
    lookback = timedelta(hours=max(1, int(settings.DIGEST_LOOKBACK_HOURS)))

    summary = {"date": day, "dry_run": dry, "cap": cap, "considered": 0, "empty": 0,
               "would_send": 0, "sent": 0, "failed": 0, "capped": 0, "already_sent_today": 0}
    summary["already_sent_today"] = (db.query(func.count(DigestLog.id))
                                     .filter(DigestLog.digest_date == day).scalar() or 0)
    remaining = max(0, cap - _emails_used_24h(db, now))
    preview: list[dict] = []
    provider = provider or get_email_provider()

    users = _sort_users(db, [u for u in _candidates(db, day) if _may_receive(db, u)])[:MAX_USERS_PER_RUN]
    started = time.monotonic()
    for user in users:
        if time.monotonic() - started > MAX_RUN_SECONDS:
            summary["time_limited"] = True
            break
        summary["considered"] += 1
        prev_end = _previous_window_end(db, user.id, now)
        since = prev_end or (now - lookback)
        content = build_content(db, user, since=since, until=now)
        if content.total == 0:
            summary["empty"] += 1
            continue
        if remaining <= 0:
            summary["capped"] += 1
            continue
        subject, body, listed = render_digest(
            user, content, now=now, max_items=settings.DIGEST_MAX_ITEMS,
            window_hours=int((now - since).total_seconds() // 3600) or 1,
        )
        if dry:
            summary["would_send"] += 1
            remaining -= 1
            if len(preview) < 8:
                preview.append({"user_id": user.id, "items": content.total, "listed": listed})
            continue

        user_id, email, total = user.id, user.email, content.total
        log = DigestLog(user_id=user_id, digest_date=day, status="claimed", item_count=total,
                        window_start=since, window_end=now)
        db.add(log)
        try:
            db.commit()          # claim BEFORE the network call
        except IntegrityError:   # someone else already claimed today's digest for this user
            db.rollback()
            summary["already_sent_today"] += 1
            continue
        log_id = log.id
        try:
            ok = bool(provider.send(email, subject, body))
        except Exception:
            logger.warning("Daily digest send raised", exc_info=True)
            ok = False
        row = db.get(DigestLog, log_id)
        if ok:
            row.status, row.sent_at = "sent", datetime.now(timezone.utc)
            db.commit()
            summary["sent"] += 1
            remaining -= 1
        else:
            db.delete(row)       # definite failure: release the claim so a later call retries
            db.commit()
            summary["failed"] += 1
            logger.warning("Daily digest stopped after a provider failure; %s sent", summary["sent"])
            break                # provider down or out of quota: do not hammer it
    if dry:
        summary["preview"] = preview
    return summary
