"""Daily Spark streaks: pure date maths plus two small DB helpers.

Everyone's "today" is the Africa/Johannesburg calendar date (SAST is UTC+2 all
year, no daylight saving), the same date the frontend uses to pick the day's
joke and wisdom, so every member sees the same spark.

Streak rules (deliberately gentle):
* current streak = consecutive days, ending today if opened today, otherwise
  ending yesterday. Not having opened *yet today* never reduces it.
* a missed day simply starts a new count at 1. Nothing is shown about losses.
* longest streak is kept for the member's own delight only.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.spark import RETENTION_DAYS, SparkOpen

try:  # zoneinfo needs the tz database; SAST has no DST so a fixed offset is exact.
    from zoneinfo import ZoneInfo

    _SAST = ZoneInfo("Africa/Johannesburg")
except Exception:  # pragma: no cover - only on hosts without tzdata
    _SAST = timezone(timedelta(hours=2))


def sast_today(now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(_SAST).date()


def compute_streaks(opened: set[date], today: date) -> tuple[int, int]:
    """(current, longest) from the set of dates the member opened."""
    if not opened:
        return 0, 0
    anchor = today if today in opened else today - timedelta(days=1)
    current = 0
    d = anchor
    while d in opened:
        current += 1
        d -= timedelta(days=1)
    longest = run = 0
    prev: date | None = None
    for d in sorted(opened):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    return current, longest


def spark_status(db: Session, user_id: str, today: date) -> dict:
    rows = db.query(SparkOpen.spark_date).filter(SparkOpen.user_id == user_id).all()
    opened = {r[0] for r in rows}
    current, longest = compute_streaks(opened, today)
    return {
        "today": today.isoformat(),
        "opened_today": today in opened,
        "current_streak": current,
        "longest_streak": longest,
        "total_opens": len(opened),
    }


def record_open(db: Session, user_id: str, today: date) -> dict:
    """Idempotent: opening twice on one day is still one day."""
    exists = db.get(SparkOpen, (user_id, today))
    if exists is None:
        db.add(SparkOpen(user_id=user_id, spark_date=today))
        db.query(SparkOpen).filter(
            SparkOpen.user_id == user_id,
            SparkOpen.spark_date < today - timedelta(days=RETENTION_DAYS),
        ).delete(synchronize_session=False)
        db.commit()
    return spark_status(db, user_id, today)
