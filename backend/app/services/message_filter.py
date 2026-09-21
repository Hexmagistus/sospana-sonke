"""Content safety filter for temporary messages.

Blocks the things that make a job-seeker platform dangerous to message on:
contact details and links (used to move victims off-platform for scams, and
personal information under POPIA), advance-fee / job-scam phrases, and threats
or abuse. Returns a short, user-facing reason, or None when the text is fine.
"""
from __future__ import annotations

import re

_URL = re.compile(r"(https?://|www\.|\b[a-z0-9-]+\.(com|co\.za|org|net|io|me|ly|app|xyz|info|biz|link)\b)", re.I)
_EMAIL = re.compile(r"[\w.+-]+\s*(@|\(at\)|\[at\])\s*[\w-]+\s*(\.|\(dot\)|\[dot\])\s*\w+", re.I)
_PHONE = re.compile(r"(\+?\d[\s().-]?){9,}")

_SCAM_PHRASES = (
    "western union", "moneygram", "send money", "processing fee", "registration fee",
    "pay to get the job", "pay for the job", "advance fee", "bank details", "bank account number",
    "id number", "send your id", "otp", "cash app", "bitcoin", "crypto investment",
    "whatsapp me", "telegram me", "dm me on", "call me on",
)
_ABUSE_PHRASES = (
    "kill yourself", "kys", "i will kill you", "i'll kill you", "i will hurt you", "i know where you live",
    "rape", "nude", "send nudes",
)


def check_message(text: str) -> str | None:
    t = text.strip()
    if not t:
        return "Message cannot be empty."
    low = t.lower()
    if _URL.search(t):
        return "Links are not allowed in messages, for your safety."
    if _EMAIL.search(t):
        return "Email addresses are not allowed in messages. Keep conversations on Sospana Sonke."
    if _PHONE.search(t):
        return "Phone numbers are not allowed in messages. Keep conversations on Sospana Sonke."
    for p in _SCAM_PHRASES:
        if p in low:
            return "This message looks like it asks for money, personal details or to move the chat elsewhere, so it was blocked."
    for p in _ABUSE_PHRASES:
        if p in low:
            return "This message contains abusive or threatening language and was blocked."
    return None
