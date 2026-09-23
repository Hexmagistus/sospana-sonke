"""File storage abstraction (blueprint sections 8 & 15).

Files (uploaded CVs, generated CVs/cover letters, reports) sit behind one small
interface with three implementations:

- `local`: disk under STORAGE_DIR. Fine for development, but NOT durable on
  Render, whose disk is wiped on every redeploy/restart.
- `db`: bytes in the `stored_files` table of the app's own Postgres. Durable,
  needs no extra account or credential; the production default (`auto`).
- `s3`: any S3-compatible bucket, for when volume outgrows the database.

Callers use `get_storage()` and never touch the backend directly.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


class Storage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> str: ...
    @abstractmethod
    def get(self, key: str) -> bytes: ...
    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorage(Storage):
    """Development storage on the local filesystem, under STORAGE_DIR."""

    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal; keys are internally generated but be defensive.
        safe = key.replace("..", "_").lstrip("/")
        p = self.base / safe
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes) -> str:
        self._path(key).write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


class S3Storage(Storage):
    """Production storage on S3-compatible object storage.

    Requires boto3 and the S3_* settings. Kept import-light so the app runs
    without boto3 installed when using local storage.
    """

    def __init__(self) -> None:
        import boto3  # imported lazily; only needed in production
        self._client = boto3.client(
            "s3", endpoint_url=settings.S3_ENDPOINT_URL, region_name=settings.S3_REGION
        )
        self._bucket = settings.S3_BUCKET

    def put(self, key: str, data: bytes) -> str:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key

    def get(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class DatabaseStorage(Storage):
    """Durable storage in the app's own database (see app/models/stored_file.py).

    Each operation uses its own short session so file writes never tangle
    with the caller's transaction. Reads fall back to the local disk for files
    written there before this backend existed (still present until the next
    restart) and copy them into the database on first access.
    """

    def __init__(self, legacy_dir: str | None = None) -> None:
        self._legacy = LocalStorage(legacy_dir) if legacy_dir else None

    @staticmethod
    def _session():
        from app.db.session import SessionLocal
        return SessionLocal()

    def put(self, key: str, data: bytes) -> str:
        from app.models.stored_file import StoredFile
        db = self._session()
        try:
            row = db.get(StoredFile, key)
            if row is None:
                db.add(StoredFile(key=key, data=data, size=len(data)))
            else:
                row.data, row.size = data, len(data)
            db.commit()
        finally:
            db.close()
        return key

    def get(self, key: str) -> bytes:
        from app.models.stored_file import StoredFile
        db = self._session()
        try:
            row = db.get(StoredFile, key)
            if row is not None:
                return bytes(row.data)
        finally:
            db.close()
        if self._legacy is not None:
            try:
                data = self._legacy.get(key)
            except FileNotFoundError:
                pass
            else:
                self.put(key, data)  # rescue it before the next restart wipes the disk
                return data
        raise FileNotFoundError(key)

    def delete(self, key: str) -> None:
        from app.models.stored_file import StoredFile
        db = self._session()
        try:
            db.query(StoredFile).filter(StoredFile.key == key).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
        if self._legacy is not None:
            self._legacy.delete(key)


def resolved_backend() -> str:
    backend = settings.STORAGE_BACKEND
    if backend == "auto":
        return "db" if settings.ENV == "production" else "local"
    return backend


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        backend = resolved_backend()
        if backend == "s3":
            _storage = S3Storage()
        elif backend == "db":
            _storage = DatabaseStorage(legacy_dir=settings.STORAGE_DIR)
        else:
            _storage = LocalStorage(settings.STORAGE_DIR)
    return _storage


def reset_storage_for_tests(base_dir: str) -> None:
    """Test helper to point storage at a temp directory."""
    global _storage
    _storage = LocalStorage(base_dir)
