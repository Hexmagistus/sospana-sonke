"""HTTP wrapper around the licence gate.

Run from cinema/discovery:
  uvicorn app.main:app --host 0.0.0.0 --port 8077

The search calls the Internet Archive advanced search API. It does not download
video and it does not use a browser.
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.licence import discover_items

app = FastAPI(title="Sospana Cinema discovery", version="1.0.0")
ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"


class DiscoverRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    rows: int = Field(default=20, ge=1, le=50)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "sospana-cinema-discovery"}


@app.get("/sources")
def sources() -> dict:
    return {
        "sources": [
            {
                "name": "Internet Archive",
                "kind": "official-search-api",
                "url": ARCHIVE_SEARCH,
                "note": "Items without an allowed licence URL are dropped.",
            }
        ]
    }


@app.post("/discover")
def discover(body: DiscoverRequest) -> dict:
    try:
        documents = search_archive(body.query, body.rows)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Internet Archive search failed: {exc}") from exc
    accepted = discover_items(documents)
    return {
        "query": body.query,
        "seen": len(documents),
        "accepted": accepted,
        "refused": len(documents) - len(accepted),
    }


def search_archive(query: str, rows: int) -> list[dict]:
    params = {
        "q": f"({query}) AND mediatype:movies",
        "rows": rows,
        "page": 1,
        "output": "json",
    }
    # fl[] must be repeated. httpx accepts a list of tuples.
    fields = [("fl[]", name) for name in ("identifier", "title", "licenseurl", "year")]
    headers = {"user-agent": os.environ.get("DISCOVERY_USER_AGENT", "SospanaCinemaBot/1.0")}
    with httpx.Client(timeout=20.0, headers=headers) as client:
        response = client.get(ARCHIVE_SEARCH, params=[*params.items(), *fields])
        response.raise_for_status()
        payload = response.json()
    docs = payload.get("response", {}).get("docs", [])
    if not isinstance(docs, list):
        raise httpx.HTTPError("Internet Archive did not return a document list.")
    return docs
