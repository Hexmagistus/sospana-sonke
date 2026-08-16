"""Deterministic page analysis: detect blockers and extract form fields.

This is the safety gate. If a CAPTCHA, login wall, MFA step, or required file upload
is present, the engine must stop and hand back to the candidate — never bypass it.
"""
from __future__ import annotations

import re

from app.automation.base import DetectedBlockers, FormFieldSpec

_CAPTCHA = re.compile(r"recaptcha|g-recaptcha|hcaptcha|cf-turnstile|h-captcha|\bcaptcha\b", re.I)
_MFA = re.compile(r"one-time (?:pin|password)|otp\b|verification code|two-factor|2fa|authenticator", re.I)
_LOGIN_WORDS = re.compile(r"\b(sign in|log ?in|please log in|create an account to apply)\b", re.I)
_PASSWORD = re.compile(r'<input[^>]*type=["\']password["\']', re.I)
_FILE = re.compile(r'<input[^>]*type=["\']file["\']', re.I)
_FORM = re.compile(r"<form\b", re.I)
_INPUT = re.compile(r"<input\b[^>]*>", re.I)

_TAG = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)
# Handle double-quoted, single-quoted, and unquoted attribute values.
_ATTR = re.compile(r"""(\w[\w-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)


def classify_page(html: str, requires_login_hint: bool = False,
                  has_captcha_hint: bool = False) -> DetectedBlockers:
    b = DetectedBlockers()
    b.captcha = bool(_CAPTCHA.search(html)) or has_captcha_hint
    b.mfa_required = bool(_MFA.search(html))
    b.login_required = requires_login_hint or (bool(_PASSWORD.search(html)) and bool(_LOGIN_WORDS.search(html)))
    b.file_upload_required = bool(_FILE.search(html))
    b.no_form = not (_FORM.search(html) or _INPUT.search(html))
    return b


def extract_form_fields(html: str) -> list[FormFieldSpec]:
    fields: list[FormFieldSpec] = []
    for tag, attr_str in _TAG.findall(html):
        attrs = {m[0].lower(): (m[1] or m[2] or m[3]) for m in _ATTR.findall(attr_str)}
        name = attrs.get("name") or attrs.get("id")
        if not name:
            continue
        input_type = (attrs.get("type") or ("textarea" if tag.lower() == "textarea" else "text")).lower()
        if input_type in ("hidden", "submit", "button", "reset", "image"):
            continue
        label = attrs.get("aria-label") or attrs.get("placeholder") or attrs.get("label") or name
        required = "required" in attr_str.lower() or attrs.get("aria-required") == "true"
        fields.append(FormFieldSpec(name=name, input_type=input_type, label=label, required=required))
    return fields
