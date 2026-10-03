"""schema.org ``JobPosting`` JSON-LD, read tolerantly.

Used by the static-HTML strategy (and by the rendered-HTML one, which reuses
it). A page that carries no JobPosting returns an empty list here; the caller
decides what that means. Nothing is guessed: a posting without a title is
dropped, and a missing field stays ``None``.

Handled beyond the plain object: ``@graph``, ``ItemList`` wrappers, lists of
postings, ``schema:JobPosting`` style type names, ``identifier`` as an object
or a bare value, several ``jobLocation`` entries, ``TELECOMMUTE`` postings,
``baseSalary`` as text, entity-escaped HTML descriptions, relative URLs, and
a repeated posting listed twice on one page.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from urllib.parse import urljoin

from app.scraper.base import RawVacancy, html_to_text

_LDJSON = re.compile(
    r"<script\b[^>]*type\s*=\s*[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_MAX_DEPTH = 6


def _is_job_posting(node: dict) -> bool:
    kinds = node.get("@type")
    for kind in (kinds if isinstance(kinds, list) else [kinds]):
        if isinstance(kind, str) and re.split(r"[:/#]", kind)[-1].lower() == "jobposting":
            return True
    return False


def _walk(node, depth: int = 0):
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, list):
        for item in node:
            yield from _walk(item, depth + 1)
    elif isinstance(node, dict):
        if _is_job_posting(node):
            yield node
            return
        for key in ("@graph", "itemListElement", "item", "mainEntity", "hasPart"):
            if key in node:
                yield from _walk(node[key], depth + 1)


def _text(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("value"))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _one_location(loc) -> str | None:
    if not isinstance(loc, dict):
        return _text(loc)
    addr = loc.get("address")
    if isinstance(addr, dict):
        parts = [_text(addr.get(k)) for k in ("addressLocality", "addressRegion", "addressCountry")]
        label = ", ".join(p for p in parts if p)
        if label:
            return label
    elif isinstance(addr, str) and addr.strip():
        return addr.strip()
    return _text(loc.get("name"))


def _location(job: dict) -> str | None:
    locs = job.get("jobLocation")
    items = locs if isinstance(locs, list) else [locs]
    labels: list[str] = []
    for loc in items:
        label = _one_location(loc) if loc else None
        if label and label not in labels:
            labels.append(label)
    return "; ".join(labels) or None


def _salary(job: dict) -> str | None:
    pay = job.get("baseSalary")
    if isinstance(pay, str):
        return pay.strip() or None
    if not isinstance(pay, dict):
        return None
    currency = _text(pay.get("currency"))
    value = pay.get("value")
    if isinstance(value, dict):
        low, high = _text(value.get("minValue")), _text(value.get("maxValue"))
        amount = _text(value.get("value"))
        unit = _text(value.get("unitText"))
        figure = f"{low}-{high}" if low and high else (amount or low or high)
    else:
        figure, unit = _text(value), None
    if not figure:
        return None
    return " ".join(x for x in (currency, figure, unit) if x)


def _description(job: dict) -> str:
    raw = job.get("description")
    if not isinstance(raw, str):
        return ""
    if "&lt;" in raw and "<" not in raw:
        raw = html_lib.unescape(raw)
    return html_to_text(raw)


def parse_job_postings(page: str, source_url: str | None = None) -> list[RawVacancy]:
    out: list[RawVacancy] = []
    seen: set[str] = set()
    for block in _LDJSON.findall(page or ""):
        try:
            data = json.loads(block.strip(), strict=False)
        except json.JSONDecodeError:
            continue
        for job in _walk(data):
            title = _text(job.get("title"))
            if not title:
                continue
            title = html_lib.unescape(title)
            external_id = _text(job.get("identifier"))
            url = _text(job.get("url"))
            if url and source_url:
                url = urljoin(source_url, url)
            key = external_id or url or title.lower()
            if key in seen:
                continue
            seen.add(key)
            emp = job.get("employmentType")
            if isinstance(emp, list):
                emp = ", ".join(str(x) for x in emp)
            remote = "TELECOMMUTE" in json.dumps(job.get("jobLocationType") or "").upper()
            out.append(RawVacancy(
                title=title,
                external_id=external_id,
                location=_location(job),
                work_mode="remote" if remote else None,
                employment_type=emp if isinstance(emp, str) else None,
                salary=_salary(job),
                posting_date=_text(job.get("datePosted")),
                closing_date=_text(job.get("validThrough")),
                description=_description(job),
                application_url=url or source_url,
                source_url=source_url,
                raw=job,
            ))
    return out
