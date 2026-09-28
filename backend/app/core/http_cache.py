"""Small HTTP cache helpers. No Redis: browsers and Cloudflare do the storing.

Public responses (the same for every visitor) get Cache-Control plus an ETag so a
repeat GET can be a 304. Authenticated reads that differ per person get a short
private lifetime so a shared cache never serves one user's body to another.
"""
from __future__ import annotations

import hashlib
import json

import orjson
from fastapi import Request, Response


def _etag_matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    parts = [p.strip() for p in header.split(",")]
    return "*" in parts or etag in parts or f"W/{etag}" in parts


def cached_json(request: Request, payload: dict, *, cache_control: str) -> Response:
    """JSON body with a strong ETag. If-None-Match returns 304 and an empty body."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    etag = '"' + hashlib.sha256(raw).hexdigest()[:16] + '"'
    headers = {
        "Cache-Control": cache_control,
        "ETag": etag,
        "Vary": "Accept-Encoding",
    }
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    # orjson for this untyped public payload. Routes that declare a response_model
    # stay on FastAPI's Pydantic serializer (faster than ORJSONResponse on 0.141,
    # and ORJSONResponse itself is deprecated there).
    return Response(content=orjson.dumps(payload), media_type="application/json", headers=headers)


def private_short_cache(response: Response, max_age: int = 15, swr: int = 45) -> None:
    """Browser-only cache for an authenticated GET. Shared caches must not store it."""
    response.headers["Cache-Control"] = f"private, max-age={max_age}, stale-while-revalidate={swr}"
    response.headers["Vary"] = "Authorization"
