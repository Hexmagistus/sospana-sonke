"""Daily Spark streaks: pure rules, SAST date handling, and the two routes."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from app.models.spark import RETENTION_DAYS, SparkOpen
from app.services.spark_service import compute_streaks, sast_today
from tests.conftest import register_and_login

API = "/api/v1"
D = date(2026, 10, 3)


def _h(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_no_opens_is_zero():
    assert compute_streaks(set(), D) == (0, 0)


def test_streak_counts_consecutive_days_ending_today():
    opened = {D, D - timedelta(days=1), D - timedelta(days=2)}
    assert compute_streaks(opened, D) == (3, 3)


def test_not_yet_opened_today_keeps_yesterdays_streak_alive():
    opened = {D - timedelta(days=1), D - timedelta(days=2)}
    assert compute_streaks(opened, D) == (2, 2)


def test_a_missed_day_starts_over_quietly_and_longest_is_remembered():
    opened = {D, D - timedelta(days=5), D - timedelta(days=6), D - timedelta(days=7), D - timedelta(days=8)}
    assert compute_streaks(opened, D) == (1, 4)


def test_old_streak_with_gap_yesterday_is_zero_not_negative():
    assert compute_streaks({D - timedelta(days=3)}, D) == (0, 1)


def test_sast_date_rolls_over_at_22_00_utc():
    assert sast_today(datetime(2026, 10, 3, 21, 59, tzinfo=timezone.utc)) == date(2026, 10, 3)
    assert sast_today(datetime(2026, 10, 3, 22, 0, tzinfo=timezone.utc)) == date(2026, 10, 4)
    assert sast_today(datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)) == date(2026, 1, 1)  # no DST in SAST


def _uid(client, tokens):
    return client.get(f"{API}/auth/me", headers=_h(tokens)).json()["id"]


def test_routes_require_login(client):
    assert client.get(f"{API}/spark/status").status_code in (401, 403)
    assert client.post(f"{API}/spark/open").status_code in (401, 403)


def test_status_does_not_write_and_open_is_idempotent(client, db_engine):
    _, tokens = register_and_login(client)
    first = client.get(f"{API}/spark/status", headers=_h(tokens)).json()
    assert first["opened_today"] is False and first["current_streak"] == 0 and first["total_opens"] == 0
    assert client.get(f"{API}/spark/status", headers=_h(tokens)).json()["total_opens"] == 0

    a = client.post(f"{API}/spark/open", headers=_h(tokens)).json()
    b = client.post(f"{API}/spark/open", headers=_h(tokens)).json()
    assert a == b
    assert a["opened_today"] is True and a["current_streak"] == 1 and a["total_opens"] == 1
    assert a["today"] == sast_today().isoformat()


def test_streak_is_per_user_and_builds_on_past_days(client, db_engine):
    _, t1 = register_and_login(client, email="one@example.com")
    u1 = _uid(client, t1)
    _, t2 = register_and_login(client, email="two@example.com")
    today = sast_today()
    s = sessionmaker(bind=db_engine)()
    for n in (1, 2, 3):
        s.add(SparkOpen(user_id=u1, spark_date=today - timedelta(days=n)))
    s.commit()
    s.close()
    before = client.get(f"{API}/spark/status", headers=_h(t1)).json()
    assert before["opened_today"] is False and before["current_streak"] == 3
    after = client.post(f"{API}/spark/open", headers=_h(t1)).json()
    assert after["current_streak"] == 4 and after["longest_streak"] == 4
    other = client.get(f"{API}/spark/status", headers=_h(t2)).json()
    assert other["current_streak"] == 0 and other["total_opens"] == 0


def test_old_rows_are_pruned_on_write(client, db_engine):
    _, t = register_and_login(client)
    u = _uid(client, t)
    s = sessionmaker(bind=db_engine)()
    s.add(SparkOpen(user_id=u, spark_date=sast_today() - timedelta(days=RETENTION_DAYS + 5)))
    s.commit()
    s.close()
    out = client.post(f"{API}/spark/open", headers=_h(t)).json()
    assert out["total_opens"] == 1


def test_export_includes_and_account_deletion_erases_opens(client, db_engine):
    _, t = register_and_login(client)
    u = _uid(client, t)
    client.post(f"{API}/spark/open", headers=_h(t))
    exported = client.get(f"{API}/account/export", headers=_h(t)).json()
    assert exported["daily_spark_opens"] == [sast_today().isoformat()]
    assert client.post(f"{API}/account/delete", headers=_h(t), json={"password": "Password123!"}).status_code == 204
    s = sessionmaker(bind=db_engine)()
    assert s.query(SparkOpen).filter(SparkOpen.user_id == u).count() == 0
    s.close()
