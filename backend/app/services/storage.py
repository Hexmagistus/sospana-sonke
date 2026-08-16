"""File storage abstraction (blueprint sections 8 & 15).

Files (uploaded CVs, later generated documents) are stored in private object
storage, never in the database. The interface below has a local-disk
implementation for development and an S3-compatible implementation for
production. Callers use `get_storage()` and never touch the backend directly.
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


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        if settings.STORAGE_BACKEND == "s3":
            _storage = S3Storage()
        else:
            _storage = LocalStorage(settings.STORAGE_DIR)
    return _storage


def reset_storage_for_tests(base_dir: str) -> None:
    """Test helper to point storage at a temp directory."""
    global _storage
    _storage = LocalStorage(base_dir)
