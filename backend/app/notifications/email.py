"""Email provider abstraction (blueprint section 31).

Swappable like the AI and payment providers. The console provider (default) simply
records messages in memory so dev and tests run offline; the SMTP provider sends
real mail in production. SMS/push can be added behind the same interface later.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings


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
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
            server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
        return True


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER == "smtp":
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
