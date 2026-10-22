"""Server-only guard for bulk id routes (anti-scraping)."""
import hmac
import logging

from fastapi import HTTPException, Request

from app.core.config import settings

HEADER = "x-internal-key"
log = logging.getLogger(__name__)


def require_internal_key(request: Request) -> None:
    expected = settings.SITEMAP_API_KEY
    if not expected:
        # Not configured yet: stay open so the sitemap keeps working. Set SITEMAP_API_KEY
        # on the backend (and the same value on Vercel) to lock these routes.
        log.warning("SITEMAP_API_KEY not set; %s is unprotected", request.url.path)
        return
    given = request.headers.get(HEADER, "")
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Forbidden")
