"""Server-only guard for bulk id routes (anti-scraping)."""
import hmac

from fastapi import HTTPException, Request

from app.core.config import settings

HEADER = "x-internal-key"


def require_internal_key(request: Request) -> None:
    expected = settings.SITEMAP_API_KEY
    if not expected:
        if settings.ENV == "production":
            raise HTTPException(status_code=404, detail="Not Found")
        return
    given = request.headers.get(HEADER, "")
    if not hmac.compare_digest(given.encode(), expected.encode()):
        # 404, not 403: don't advertise that the route exists.
        raise HTTPException(status_code=404, detail="Not Found")
