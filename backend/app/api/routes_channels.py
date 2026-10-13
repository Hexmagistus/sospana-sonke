"""USSD and WhatsApp callbacks. Both stay off until the owner sets the account values."""
from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.channel_menu import ussd_screen, whatsapp_reply
from app.services.whatsapp_send import deliver_whatsapp

router = APIRouter(tags=["channels"])

_OFF = "USSD is off. No shortcode is configured.\n"
_WA_OFF = "WhatsApp is off. No phone number is configured.\n"


def _plain(text: str, status: int = 200) -> Response:
    return Response(text, status_code=status, media_type="text/plain")


def _ussd_on() -> bool:
    return bool(settings.USSD_ENABLED and settings.USSD_CALLBACK_SECRET)


def _secret_ok(header: str | None, query: str | None) -> bool:
    configured = settings.USSD_CALLBACK_SECRET or ""
    supplied = header or query or ""
    return bool(configured) and hmac.compare_digest(supplied, configured)


def _whatsapp_on() -> bool:
    return bool(
        settings.WHATSAPP_VERIFY_TOKEN
        and settings.WHATSAPP_TOKEN
        and settings.WHATSAPP_PHONE_NUMBER_ID
        and settings.WHATSAPP_APP_SECRET
    )


@router.post("/ussd")
async def ussd_callback(
    request: Request,
    db: Session = Depends(get_db),
    x_ussd_secret: str | None = Header(default=None, alias="X-Ussd-Secret"),
    secret: str | None = Query(default=None),
):
    if not _ussd_on():
        return _plain(_OFF, 404)
    if not _secret_ok(x_ussd_secret, secret):
        return _plain("Unauthorised.\n", 401)
    form = await request.form()
    text = str(form.get("text") or "")
    phone = str(form.get("phoneNumber") or "")
    return _plain(ussd_screen(text, db, phone) + "\n")


@router.get("/whatsapp")
def whatsapp_verify(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    if not _whatsapp_on():
        return _plain(_WA_OFF, 404)
    if hub_mode == "subscribe" and hmac.compare_digest(hub_verify_token, settings.WHATSAPP_VERIFY_TOKEN or ""):
        return _plain(hub_challenge)
    return _plain("Unauthorised.\n", 403)


@router.post("/whatsapp")
async def whatsapp_inbound(request: Request, db: Session = Depends(get_db)):
    if not _whatsapp_on():
        return _plain(_WA_OFF, 404)
    body = await request.body()
    digest = hmac.new((settings.WHATSAPP_APP_SECRET or "").encode(), body, hashlib.sha256).hexdigest()
    header = request.headers.get("x-hub-signature-256") or ""
    if not hmac.compare_digest(header, f"sha256={digest}"):
        return _plain("Unauthorised.\n", 401)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return _plain("OK\n")
    message = _first_text(payload)
    if message is None:
        return _plain("OK\n")
    reply = whatsapp_reply(message["text"], db, message["from"])
    deliver_whatsapp(message["from"], reply)
    return _plain("OK\n")


def _first_text(payload: object) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            for message in value.get("messages") or []:
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                text = (message.get("text") or {}).get("body")
                sender = message.get("from")
                if isinstance(text, str) and isinstance(sender, str):
                    return {"text": text, "from": sender}
    return None
