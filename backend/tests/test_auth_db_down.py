"""Auth endpoints answer 503 with a friendly message when the database is down."""
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db


class _DeadSession:
    def __getattr__(self, name):
        def boom(*a, **k):
            raise OperationalError("SELECT 1", {}, Exception("402 exceeded the quota"))
        return boom


def test_login_returns_503_when_db_down(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "init_db", lambda: None)
    app = main.create_app()
    app.dependency_overrides[get_db] = lambda: _DeadSession()
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "x" * 10})
        assert r.status_code == 503
        assert "Sign-in is paused during maintenance" in r.json()["detail"]
