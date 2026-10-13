"""USSD and WhatsApp menus over stored South African roles. No message is sent here."""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.sms_alert import SmsAlert
from app.models.vacancy import Vacancy

SCREEN_LIMIT = 182
_PHONE = re.compile(r"^\+?[0-9]{8,15}$")
_SHORTCODE = re.compile(r"\*\d+#")

CATEGORIES = (
    ("1", "job", "Job"),
    ("2", "internship", "Internship"),
    ("3", "learnership", "Learnership"),
    ("4", "bursary", "Bursary"),
    ("5", "graduate_programme", "Graduate"),
)
PROVINCES = (
    ("1", "Eastern Cape", "E Cape"),
    ("2", "Free State", "Free State"),
    ("3", "Gauteng", "Gauteng"),
    ("4", "KwaZulu-Natal", "KZN"),
    ("5", "Limpopo", "Limpopo"),
    ("6", "Mpumalanga", "Mpumalanga"),
    ("7", "Northern Cape", "N Cape"),
    ("8", "North West", "North West"),
    ("9", "Western Cape", "W Cape"),
)


def fit(text: str) -> str:
    if len(text) <= SCREEN_LIMIT:
        return text
    return text[: SCREEN_LIMIT - 3] + "..."


def clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().replace(" ", "")
    if not _PHONE.fullmatch(text):
        return None
    return text


def matching_titles(db: Session, *, kind: str | None = None, province: str | None = None) -> list[str]:
    today = date.today()
    query = db.query(Vacancy.title).filter(
        Vacancy.is_open.is_(True),
        Vacancy.deleted_at.is_(None),
        Vacancy.country == "South Africa",
        or_(Vacancy.closing_date.is_(None), Vacancy.closing_date >= today),
    )
    if kind:
        query = query.filter(Vacancy.opportunity_type == kind)
    if province:
        query = query.filter(Vacancy.province == province)
    rows = query.order_by(Vacancy.last_seen_at.desc()).limit(3).all()
    return [str(row[0])[:40] for row in rows]


def save_sms_request(db: Session, phone: str) -> bool:
    cleaned = clean_phone(phone)
    if not cleaned:
        return False
    row = db.query(SmsAlert).filter(SmsAlert.phone == cleaned).one_or_none()
    if row is None:
        db.add(SmsAlert(phone=cleaned, active=True))
    else:
        row.active = True
    db.commit()
    return True


def _list(label: str, titles: list[str]) -> str:
    if not titles:
        return fit(f"END {label}\nNo stored role matches.")
    lines = [f"END {label}"] + [f"{index}. {title}" for index, title in enumerate(titles, start=1)]
    return fit("\n".join(lines))


def _main() -> str:
    return fit("CON Sospana Sonke\n1 Categories\n2 Province\n3 Learnerships\n4 Bursaries\n5 Save number for SMS")


def ussd_screen(text: str, db: Session, phone: str | None) -> str:
    parts = [part for part in (text or "").split("*") if part]
    if not parts:
        return _main()
    if parts[0] == "1" and len(parts) == 1:
        lines = ["CON Categories"] + [f"{key} {label}" for key, _kind, label in CATEGORIES] + ["0 Back"]
        return fit("\n".join(lines))
    if parts[0] == "1" and len(parts) > 1:
        chosen = next((item for item in CATEGORIES if item[0] == parts[1]), None)
        if chosen is None:
            return _main()
        return _list(chosen[2], matching_titles(db, kind=chosen[1]))
    if parts[0] == "2" and len(parts) == 1:
        lines = ["CON Province"] + [f"{key} {label}" for key, _name, label in PROVINCES] + ["0 Back"]
        return fit("\n".join(lines))
    if parts[0] == "2" and len(parts) > 1:
        chosen = next((item for item in PROVINCES if item[0] == parts[1]), None)
        if chosen is None:
            return _main()
        return _list(chosen[1], matching_titles(db, province=chosen[1]))
    if parts[0] == "3":
        return _list("Learnerships", matching_titles(db, kind="learnership"))
    if parts[0] == "4":
        return _list("Bursaries", matching_titles(db, kind="bursary"))
    if parts[0] == "5" and len(parts) == 1:
        return fit("CON Save this number for SMS alerts?\n1 Yes\n0 Back\nNo SMS is sent yet.")
    if parts[0] == "5" and parts[1] == "1":
        if save_sms_request(db, phone):
            return fit("END Saved. No SMS was sent.")
        return fit("END This number cannot be saved. No SMS was sent.")
    return _main()


def whatsapp_reply(text: str, db: Session, phone: str | None) -> str:
    screen = ussd_screen(text, db, phone)
    if screen.startswith("CON "):
        return screen[4:]
    if screen.startswith("END "):
        return screen[4:]
    return screen


def contains_shortcode(text: str) -> bool:
    return _SHORTCODE.search(text) is not None
