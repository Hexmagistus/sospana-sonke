"""External cron trigger (blueprint section 22).

Lets a free external scheduler (GitHub Actions, cron-job.org, …) run a scheduler
job on a cadence WITHOUT an admin login, authenticated by a shared secret.

Security:
- Disabled unless CRON_SECRET is configured.
- The secret must be supplied in the `X-Cron-Secret` header. (A `?token=` query
  parameter used to be accepted too, but secrets in URLs end up in proxy/access
  logs and browser history -- flagged by the 2026-09-24 DAST scan -- so it's gone.)
  Compared with hmac.compare_digest (constant time) and rate-limited per IP.
- Only reads public listings / runs known jobs — no destructive actions.
"""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.rate_limit import limiter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.notification import JobRunResponse
from app.scheduler.registry import JOBS
from app.scheduler.runner import run_job, UnknownJob

router = APIRouter(tags=["cron"])


def _authorise(header_secret: str | None) -> None:
    configured = settings.CRON_SECRET
    if not configured:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    supplied = header_secret or ""
    if not hmac.compare_digest(supplied, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret.")


@router.post("/cron/run/{name}", response_model=JobRunResponse)
@limiter.limit("30/minute")
def run_scheduled_job(
    request: Request,
    name: str,
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
):
    _authorise(x_cron_secret)
    try:
        return JobRunResponse.model_validate(run_job(db, name))
    except UnknownJob:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Unknown job '{name}'. Known jobs: {', '.join(JOBS)}.")
