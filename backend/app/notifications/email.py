"""Email provider abstraction (blueprint section 31).

Swappable like the AI and payment providers. The console provider (default)
records messages in memory so dev and tests run offline. The SMTP provider
sends real mail where outbound SMTP is allowed. When BREVO_API_KEY is set,
every caller goes through Brevo's HTTPS transactional API instead: Render's
free plan cannot open SMTP ("Network is unreachable").

POPIA stays with the callers. This module does not decide who may be mailed.
A tagging notice is emailed only when the caller has already checked an
explicit tagging-email yes, and the platform mail switch is on. Password
reset, verification, the owner login alert, and the one-time settings email
are account mail.
"""
from __future__ import annotations

import html
import logging
import re
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_TIMEOUT_SECONDS = 10.0

# Set when Brevo rejects the account (auth or the free daily quota). Further
# sends return immediately so a notification batch cannot hammer the API.
_brevo_halted = False
_brevo_halt_logged = False

_FROM_ADDRESS = re.compile(r"<([^<>]+)>")
_QUOTA_HINTS = ("quota", "credit", "daily limit", "too many request", "rate limit")
_AUTH_HINTS = ("unauthorized", "unauthorised", "api-key", "api key", "invalid key", "authentication")


class EmailProvider(ABC):
    name: str = "base"

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> bool: ...


class ConsoleEmailProvider(EmailProvider):
    name = "console"
    #: In-memory outbox, useful for local inspection and tests.
    outbox: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> bool:
        self.outbox.append({"to": to, "subject": subject, "body": body})
        print(f"[email:console] to={to} subject={subject!r}")
        return True


class SMTPEmailProvider(EmailProvider):
    name = "smtp"

    def send(self, to: str, subject: str, body: str) -> bool:
        import smtplib
        from email.mime.text import MIMEText
        if not settings.SMTP_HOST:
            return False
        html_body = _html_from_text(body)
        if "<a " in html_body:
            from email.mime.multipart import MIMEMultipart
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
        else:
            msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
            server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
        return True


def reset_brevo_send_state() -> None:
    """Test hook. Production clears this only by restarting the process."""
    global _brevo_halted, _brevo_halt_logged
    _brevo_halted = False
    _brevo_halt_logged = False


def _halt_brevo(reason: str, status: int | None = None) -> None:
    """Stop further Brevo calls and write a single line with no message content."""
    global _brevo_halted, _brevo_halt_logged
    _brevo_halted = True
    if _brevo_halt_logged:
        return
    _brevo_halt_logged = True
    if status is None:
        logger.warning(
            "Brevo email stopped (%s); further sends are skipped until the process restarts",
            reason,
        )
    else:
        logger.warning(
            "Brevo email stopped (%s, HTTP %s); further sends are skipped until the process restarts",
            reason,
            status,
        )


def _halt_category(status: int, body: str) -> str | None:
    if status in (401, 403):
        return "auth"
    if status in (402, 429):
        return "quota"
    if not 400 <= status < 500:
        return None
    # Classified locally and never logged. A short slice is enough for the hint.
    sample = body[:500].lower()
    if any(hint in sample for hint in _QUOTA_HINTS):
        return "quota"
    if any(hint in sample for hint in _AUTH_HINTS):
        return "auth"
    return None


def _html_from_text(body: str) -> str:
    """Escape every line. A line that is only an http(s) URL becomes a button."""
    from app.notifications.links import validated_notice_url

    blocks: list[str] = []
    for line in body.split("\n"):
        url = None
        try:
            url = validated_notice_url(line)
        except ValueError:
            url = None
        if url and line.strip() == url:
            href = html.escape(url, quote=True)
            is_digest = body.startswith("Your daily updates")
            if is_digest and "/digest/unsubscribe" in url:
                label = "Unsubscribe"
            elif is_digest and url.rstrip("/").endswith("/agent"):
                label = "See everything in the app"
            elif is_digest and not (url.rstrip("/").endswith("/preferences")
                                    or url.rstrip("/").endswith("/privacy")):
                label = "View careers page"
            elif "Tagged by the Sospana Sonke team" in body:
                label = "Open this listing"
            elif url.rstrip("/").endswith("/preferences"):
                label = "Choose my preferences"
            elif url.rstrip("/").endswith("/privacy"):
                label = "Privacy Policy"
            else:
                label = "Open"
            blocks.append(
                '<p><a href="' + href + '" '
                'style="display:inline-block;background:#0b2447;color:#ffffff;'
                'padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:700">'
                + html.escape(label) + "</a></p>"
            )
        else:
            blocks.append("<p>" + html.escape(line, quote=True) + "</p>")
    return "\n".join(blocks)


def _reply_to(sender_email: str) -> dict | None:
    raw = (settings.EMAIL_FROM or "").strip()
    if not raw:
        return None
    match = _FROM_ADDRESS.search(raw)
    address = (match.group(1) if match else raw).strip()
    if "@" not in address or address.lower() == sender_email.lower():
        return None
    name = raw.split("<", 1)[0].strip().strip('"') or _sender_name()
    return {"email": address, "name": name}


def _sender_name() -> str:
    return (settings.BREVO_SENDER_NAME or "").strip() or "Sospana Sonke"


def _post_brevo(url: str, *, headers: dict, payload: dict, timeout: float) -> httpx.Response:
    with httpx.Client(timeout=timeout) as client:
        return client.post(url, headers=headers, json=payload)


class BrevoEmailProvider(EmailProvider):
    name = "brevo"

    def send(self, to: str, subject: str, body: str) -> bool:
        if _brevo_halted:
            return False
        api_key = (settings.BREVO_API_KEY or "").strip()
        sender_email = (settings.BREVO_SENDER_EMAIL or "").strip()
        if not api_key:
            return False
        if not sender_email:
            _halt_brevo("missing_sender")
            return False

        payload: dict = {
            "sender": {"name": _sender_name(), "email": sender_email},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body,
            "htmlContent": _html_from_text(body),
        }
        reply = _reply_to(sender_email)
        if reply is not None:
            payload["replyTo"] = reply

        try:
            response = _post_brevo(
                BREVO_URL,
                headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
                payload=payload,
                timeout=BREVO_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            # Class name only. httpx messages can echo the request.
            logger.warning("Brevo send failed (%s)", type(exc).__name__)
            return False

        if 200 <= response.status_code < 300:
            return True

        try:
            response_text = response.text or ""
        except Exception:
            response_text = ""
        category = _halt_category(response.status_code, response_text)
        if category is not None:
            _halt_brevo(category, response.status_code)
            return False
        logger.warning("Brevo send failed (HTTP %s)", response.status_code)
        return False


def get_email_provider() -> EmailProvider:
    if (settings.BREVO_API_KEY or "").strip():
        return BrevoEmailProvider()
    if settings.EMAIL_PROVIDER == "smtp":
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
