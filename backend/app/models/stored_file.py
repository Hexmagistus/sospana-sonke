"""Binary file blobs kept in Postgres (the `db` storage backend).

Render's free instance has an ephemeral disk: everything under ./storage is
wiped on every redeploy and restart, which silently deleted uploaded CVs and
generated documents. Storing the bytes in the database we already run (Neon)
makes them durable without another account, bucket or credential. Files are
small (CVs are capped at MAX_UPLOAD_MB, generated DOCX/PDFs are ~40 KB).
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StoredFile(Base):
    __tablename__ = "stored_files"

    key: Mapped[str] = mapped_column(String(512), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
