"""Job matching has been removed (it kept matching against old posts).

Every route that used to run, list or act on a candidate match answers **410 Gone**
with a plain message, so an old bookmark, cached app tab or stale client gets a clear
answer instead of a 404 or a 500. No match is computed or returned any more.

Stored data is untouched: the ``candidate_matches`` table and its rows stay in the
database (nothing is dropped or deleted), they are just never read by the app.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["matches"])

_GONE = {"detail": "Job matching has been removed. Browse vacancies and companies directly."}
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


@router.api_route("/matches", methods=_METHODS, include_in_schema=False)
@router.api_route("/matches/{path:path}", methods=_METHODS, include_in_schema=False)
@router.api_route("/admin/match-config", methods=_METHODS, include_in_schema=False)
def matching_removed(path: str = "") -> JSONResponse:
    return JSONResponse(_GONE, status_code=410)
