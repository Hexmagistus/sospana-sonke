"""Boot DDL must not hang, and notification email must not hold a transaction."""
import uuid

from app.core import security
from app.core.config import settings
from app.db import session as db_session
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import create_notification


def test_neon_pooler_connect_args_never_carry_startup_options():
    """pgbouncer rejects idle_in_transaction_session_timeout in libpq options."""
    url = "postgresql://user:s3cret@ep-example-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    poisoned = {"options": "-c idle_in_transaction_session_timeout=60000"}
    args = db_session.postgres_connect_args(url, poisoned)
    assert "options" not in args
    assert args == {}
    assert db_session.postgres_connect_args(url) == {}
    direct = "postgresql://user:s3cret@ep-example.eu-central-1.aws.neon.tech/neondb"
    assert "options" not in db_session.postgres_connect_args(direct)


def test_postgres_ddl_guards_set_lock_and_statement_timeout():
    guards = db_session._postgres_ddl_guards()
    assert any("lock_timeout" in sql and "5s" in sql for sql in guards)
    assert any("statement_timeout" in sql for sql in guards)
    assert all(sql.startswith("SET LOCAL ") for sql in guards)


def test_execute_ddl_skips_instead_of_raising(monkeypatch):
    class _Boom:
        def __enter__(self):
            raise RuntimeError("canceling statement due to lock timeout")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(db_session.engine, "begin", lambda: _Boom())
    monkeypatch.setattr(db_session.time, "sleep", lambda _seconds: None)
    assert db_session._execute_ddl("ALTER TABLE users ADD COLUMN example BOOLEAN", attempts=2) is False


def test_email_failure_commits_before_send_and_closes_the_transaction(db, monkeypatch):
    user = User(
        email="notify-boot@example.com",
        password_hash=security.hash_password("Password123!"),
        first_name="Naledi",
        last_name="Dlamini",
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(settings, "NOTIFY_EMAILS", True)
    seen = {}

    def boom(_self, to, subject, body):
        seen["open_during_send"] = db.in_transaction()
        raise OSError(101, "Network is unreachable")

    monkeypatch.setattr("app.notifications.email.ConsoleEmailProvider.send", boom)
    related = str(uuid.uuid4())
    note = create_notification(
        db, user_id=user.id, to_email=user.email, type="strong_match",
        title="A match", body="Details", related_type="match", related_id=related,
        send_email=True,
    )
    assert seen["open_during_send"] is False
    assert note is not None
    assert note.email_sent is False
    assert not db.in_transaction()
    stored = db.query(Notification).filter_by(user_id=user.id, related_id=related).one()
    assert stored.email_sent is False
    db.rollback()
