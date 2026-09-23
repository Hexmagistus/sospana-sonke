"""Durable database-backed file storage (STORAGE_BACKEND=db / auto in production)."""
import pytest

from app.core.config import settings
from app.services.storage import DatabaseStorage, LocalStorage, resolved_backend


@pytest.fixture()
def db_storage(db_engine, tmp_path, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from app.db import session as session_mod
    monkeypatch.setattr(session_mod, "SessionLocal", sessionmaker(bind=db_engine))
    return DatabaseStorage(legacy_dir=str(tmp_path / "legacy"))


def test_put_get_overwrite_delete(db_storage):
    db_storage.put("cvs/u1/a.pdf", b"%PDF-1")
    assert db_storage.get("cvs/u1/a.pdf") == b"%PDF-1"
    db_storage.put("cvs/u1/a.pdf", b"%PDF-2")
    assert db_storage.get("cvs/u1/a.pdf") == b"%PDF-2"
    db_storage.delete("cvs/u1/a.pdf")
    with pytest.raises(FileNotFoundError):
        db_storage.get("cvs/u1/a.pdf")


def test_legacy_disk_file_is_rescued_into_database(db_storage, tmp_path):
    LocalStorage(str(tmp_path / "legacy")).put("cvs/u2/old.docx", b"PK-old")
    assert db_storage.get("cvs/u2/old.docx") == b"PK-old"
    # Simulate Render wiping the disk on restart: the DB copy survives.
    (tmp_path / "legacy" / "cvs" / "u2" / "old.docx").unlink()
    assert db_storage.get("cvs/u2/old.docx") == b"PK-old"


def test_auto_backend_is_db_in_production(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "auto")
    monkeypatch.setattr(settings, "ENV", "production")
    assert resolved_backend() == "db"
    monkeypatch.setattr(settings, "ENV", "development")
    assert resolved_backend() == "local"


def test_missing_file_download_returns_friendly_410(client, monkeypatch):
    from tests.conftest import register_and_login
    _, tokens = register_and_login(client)
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    up = client.post("/api/v1/cv", headers=h,
                     files={"file": ("cv.txt", b"Water treatment operator. 5 years experience.", "text/plain")})
    if up.status_code >= 300:
        pytest.skip(f"upload path rejected plain text ({up.status_code})")
    cv_id = up.json()["id"]
    # Make the stored bytes vanish behind the record, as a Render restart used to.
    import app.services.storage as sm
    monkeypatch.setattr(sm._storage, "get", lambda k: (_ for _ in ()).throw(FileNotFoundError(k)))
    r = client.get(f"/api/v1/cv/{cv_id}/download", headers=h)
    assert r.status_code == 410
    assert "re-upload" in r.json()["detail"]


def test_account_deletion_erases_cv_files_and_text(client):
    from tests.conftest import register_and_login
    import app.services.storage as sm
    _, tokens = register_and_login(client)
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    up = client.post("/api/v1/cv", headers=h,
                     files={"file": ("cv.txt", b"Jane Doe. Water treatment operator. 5 years.", "text/plain")})
    assert up.status_code < 300, up.text
    cv_id = up.json()["id"]
    assert client.get(f"/api/v1/cv/{cv_id}/download", headers=h).status_code == 200
    from app.models.cv import CV
    from app.db.session import get_db
    from app.main import app as fastapi_app
    db = next(fastapi_app.dependency_overrides[get_db]())
    key = db.get(CV, cv_id).storage_key
    db.close()
    assert sm._storage.get(key)
    assert client.post("/api/v1/account/delete", headers=h, json={"password": "Password123!"}).status_code == 204
    with pytest.raises(FileNotFoundError):
        sm._storage.get(key)
    db = next(fastapi_app.dependency_overrides[get_db]())
    row = db.get(CV, cv_id)
    assert row.extracted_text is None and row.structured is None and row.deleted_at is not None
    db.close()
