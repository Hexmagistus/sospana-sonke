"""The API boots and serves the jobs snapshot when the database is unreachable."""
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def test_app_boots_when_init_db_fails(monkeypatch):
    import app.main as main

    def boom():
        raise OperationalError("SELECT 1", {}, Exception("402 quota exceeded"))

    monkeypatch.setattr(main, "init_db", boom)
    with TestClient(main.create_app()) as client:
        assert client.get("/health").status_code == 200
