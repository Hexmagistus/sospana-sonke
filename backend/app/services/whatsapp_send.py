"""Send one WhatsApp reply. Called only when the owner has set the account values."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.core.config import settings


def deliver_whatsapp(to: str, body: str) -> bool:
    token = settings.WHATSAPP_TOKEN
    number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    if not token or not number_id:
        return False
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:1000]},
    }).encode()
    request = urllib.request.Request(
        f"https://graph.facebook.com/v21.0/{number_id}/messages",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False
