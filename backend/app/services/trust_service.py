"""Trust & safety: heuristic scam/quality signals on a vacancy (blueprint section 18).

Deliberately conservative and explainable -- every flag names exactly which
signal fired, and this never blocks a listing from appearing or auto-deletes
anything. It surfaces flags for a human (admin) to review, and lets a candidate
see the same signals a report dialog would ask about. False positives are
expected and acceptable; silent scams are not.
"""
from __future__ import annotations

import re

# Phrases that commonly indicate an upfront-payment scam -- legitimate SA
# employers do not ask a candidate to pay to apply, interview, or "process" a job.
_PAYMENT_REQUEST_PATTERNS = [
    r"registration fee", r"processing fee", r"application fee", r"pay(?:ment)? (?:is )?required to apply",
    r"deposit required", r"send.{0,20}(?:registration|admin) fee", r"activation fee",
    r"training fee (?:is )?required", r"pay .{0,15}(?:before|to secure)",
]

# Contact/data requests that are a red flag on an unsolicited job ad specifically
# (a normal application process on an employer's own ATS never needs this framed
# as "send us your ID/bank details directly" outside of that system).
_DATA_REQUEST_PATTERNS = [
    r"send.{0,20}(?:copy of your )?id (?:number|document|copy)",
    r"whatsapp.{0,20}(?:id|bank|banking)", r"banking details.{0,20}(?:to apply|upfront|before)",
]

_VAGUE_URGENCY_PATTERNS = [
    r"urgent(?:ly)? hiring", r"immediate start.{0,10}no experience", r"limited slots",
    r"earn up to r?\s?\d+.{0,10}(?:per day|daily)",
]

_PAYMENT_RE = re.compile("|".join(_PAYMENT_REQUEST_PATTERNS), re.IGNORECASE)
_DATA_RE = re.compile("|".join(_DATA_REQUEST_PATTERNS), re.IGNORECASE)
_URGENCY_RE = re.compile("|".join(_VAGUE_URGENCY_PATTERNS), re.IGNORECASE)

# Above this, a monthly ZAR figure on an entry-level-sounding ad is treated as an
# unrealistic-salary signal worth a human look, not proof of anything by itself.
UNREALISTIC_MONTHLY_SALARY_ZAR = 300_000


def scan_for_trust_flags(
    *, title: str | None, description: str | None, salary_min: int | None,
    salary_max: int | None, application_url: str | None, source_url: str | None,
) -> list[str]:
    """Returns a list of flag codes (never raises, never fabricates a verdict)."""
    flags: list[str] = []
    blob = f"{title or ''} {description or ''}"

    if _PAYMENT_RE.search(blob):
        flags.append("payment_request")
    if _DATA_RE.search(blob):
        flags.append("suspicious_data_request")
    if _URGENCY_RE.search(blob):
        flags.append("vague_urgency_language")
    if salary_max is not None and salary_max > UNREALISTIC_MONTHLY_SALARY_ZAR:
        flags.append("unrealistic_salary")
    if not application_url and not source_url:
        flags.append("missing_application_link")

    return flags


# Human-readable labels for the frontend / admin queue -- kept alongside the
# codes so both sides of the stack agree on wording without duplicating it.
TRUST_FLAG_LABELS = {
    "payment_request": "Mentions a fee or payment to apply",
    "suspicious_data_request": "Asks for ID/banking details outside a normal process",
    "vague_urgency_language": "Uses vague urgency language common in scam ads",
    "unrealistic_salary": "Salary figure looks unrealistically high for the role",
    "missing_application_link": "No application or source link provided",
}
