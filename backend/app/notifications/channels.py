"""SMS and push notification channels (blueprint section 31).

Same swappable pattern as email: console providers (record to an in-memory outbox,
so dev/tests run offline) plus real provider interfaces for production (Twilio for
SMS, FCM for push). Selected by config.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings


class SMSProvider(ABC):
    @abstractmethod
    def send(self, to: str, body: str) -> bool: ...


class ConsoleSMSProvider(SMSProvider):
    outbox: list[dict] = []

    def send(self, to: str, body: str) -> bool:
        self.outbox.append({"to": to, "body": body})
        return True


class TwilioSMSProvider(SMSProvider):
    def send(self, to: str, body: str) -> bool:
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM):
            return False
        import httpx
        resp = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            data={"To": to, "From": settings.TWILIO_FROM, "Body": body}, timeout=20.0,
        )
        return resp.status_code < 300


class PushProvider(ABC):
    @abstractmethod
    def send(self, token: str, title: str, body: str) -> bool: ...


class ConsolePushProvider(PushProvider):
    outbox: list[dict] = []

    def send(self, token: str, title: str, body: str) -> bool:
        self.outbox.append({"token": token, "title": title, "body": body})
        return True


class FCMPushProvider(PushProvider):
    def send(self, token: str, title: str, body: str) -> bool:  # pragma: no cover - prod only
        # Wire an FCM/web-push HTTP call here with server credentials.
        return False


def get_sms_provider() -> SMSProvider:
    return TwilioSMSProvider() if settings.SMS_PROVIDER == "twilio" else ConsoleSMSProvider()


def get_push_provider() -> PushProvider:
    return FCMPushProvider() if settings.PUSH_PROVIDER == "fcm" else ConsolePushProvider()
