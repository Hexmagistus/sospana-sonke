"""Public copy of one official labour table. No account and no microdata."""
from fastapi import APIRouter, Request, Response

from app.core.rate_limit import limiter
from app.services.labour_stats import public_document

router = APIRouter(prefix="/labour", tags=["labour"])


@router.get("/south-africa")
@limiter.limit("60/minute")
def south_africa_labour(request: Request, response: Response):
    """Unemployment rates by province from the stored Stats SA table.

    The question is not relevant here. A missing file returns an empty document
    rather than a guessed rate.
    """
    response.headers["Cache-Control"] = "public, max-age=3600"
    return public_document()
