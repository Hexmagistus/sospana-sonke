"""Decide whether a licence URL is one Sospana Cinema may offer for playback."""

from __future__ import annotations

REJECT_PARTS = ("by-nc", "by-nd", "nc-sa", "nc-nd")
IDENTIFIER = __import__("re").compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,180}$")


def licence_kind(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    value = url.strip().lower()
    if not value.startswith(("http://", "https://")):
        return None
    if any(part in value for part in REJECT_PARTS):
        return None
    if "publicdomain/zero" in value or value.rstrip("/").endswith("zero/1.0"):
        return "cc0"
    if (
        "publicdomain/mark" in value
        or "public-domain" in value
        or "/licenses/publicdomain" in value
        or value.rstrip("/").endswith("/publicdomain")
    ):
        return "public-domain"
    if "/licenses/by-sa/" in value or value.rstrip("/").endswith("/licenses/by-sa"):
        return "cc-by-sa"
    if "/licenses/by/" in value or value.rstrip("/").endswith("/licenses/by"):
        return "cc-by"
    return None


def candidate_from_item(item: dict) -> dict | None:
    """Return an embed candidate, or None. Never invents a playback URL."""
    kind = licence_kind(item.get("licenseurl"))
    identifier = str(item.get("identifier") or "").strip()
    title = item.get("title")
    title = title.strip() if isinstance(title, str) else ""
    evidence = item.get("licenseurl")
    if not kind or not title or not IDENTIFIER.match(identifier) or not isinstance(evidence, str):
        return None
    return {
        "title": title,
        "identifier": identifier,
        "year": item.get("year"),
        "licenceType": kind,
        "licenceEvidenceUrl": evidence,
        "sourceRecordUrl": f"https://archive.org/details/{identifier}",
        "authorizedEmbedUrl": f"https://archive.org/embed/{identifier}",
        "rightsVerified": True,
    }


def discover_items(items: list[dict]) -> list[dict]:
    found = []
    for item in items:
        candidate = candidate_from_item(item)
        if candidate:
            found.append(candidate)
    return found
