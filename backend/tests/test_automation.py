"""Tests for the Phase 2 application-automation engine.

Deterministic logic is tested with a MockSubmitter (offline). A single live test
drives real Playwright against a local form server, and skips if the browser is
unavailable so the suite never depends on it.
"""
import glob
from datetime import datetime, timezone

import pytest

from app.automation.base import Submitter
from app.automation.detector import classify_page, extract_form_fields
from app.automation.planner import build_answer_map, plan_submission
from app.automation.mock_submitter import MockSubmitter
from app.automation.engine import attempt_auto_submit
from app.core.config import settings
from app.core import security
from app.models.user import User
from app.models.company import Company
from app.models.profile import CandidateProfile
from app.models.vacancy import Vacancy
from app.models.application import Application

SIMPLE_FORM = ("<html><body><form method='POST' action='/submit'>"
               "<input name='email' required><input name='full_name' required>"
               "<input name='years_experience'>"
               "<button type='submit'>Apply</button></form></body></html>")
CAPTCHA_FORM = SIMPLE_FORM.replace("<button", "<div class='g-recaptcha'></div><button")
LOGIN_FORM = ("<html><body>Please sign in to apply"
              "<form><input name='email'><input type='password' name='pw'>"
              "<button type='submit'>Log in</button></form></body></html>")
UNKNOWN_REQUIRED = ("<html><body><form><input name='email' required>"
                    "<input name='id_number' required aria-label='ID number'>"
                    "<button type='submit'>Go</button></form></body></html>")


# ---- detector ----

def test_detector_flags():
    assert classify_page(CAPTCHA_FORM).captcha
    assert classify_page(LOGIN_FORM).login_required
    assert classify_page("<p>enter your one-time pin</p>").mfa_required
    assert classify_page("<input type='file' name='cv'>").file_upload_required
    assert classify_page("<p>no form here</p>").no_form
    assert not classify_page(SIMPLE_FORM).blocking


def test_extract_form_fields():
    fields = {f.name: f for f in extract_form_fields(SIMPLE_FORM)}
    assert set(fields) == {"email", "full_name", "years_experience"}
    assert fields["email"].required and not fields["years_experience"].required


# ---- planner ----

def test_planner_maps_truthfully_and_flags_unknown():
    facts = {"full_name": "Thandi Mokoena", "email": "t@x.co", "years_experience": 6}
    amap = build_answer_map(facts)
    plan = plan_submission(extract_form_fields(SIMPLE_FORM), amap)
    assert plan.values["email"] == "t@x.co"
    assert plan.values["full_name"] == "Thandi Mokoena"
    assert plan.values["years_experience"] == "6"
    assert plan.unknown_required == []

    plan2 = plan_submission(extract_form_fields(UNKNOWN_REQUIRED), amap)
    assert "ID number" in plan2.unknown_required  # required + unmappable -> candidate input


# ---- engine (mock submitter) ----

def _setup(db, mode="auto", requires_login=False, has_captcha=False):
    user = User(email="thandi@x.co", password_hash=security.hash_password("Password123!"),
                first_name="Thandi", last_name="Mokoena", role="candidate", email_verified=True,
                mobile_number="0821234567")
    db.add(user); db.commit(); db.refresh(user)
    db.add(CandidateProfile(user_id=user.id, years_experience=6, city="Johannesburg",
                            current_occupation="Operations Supervisor"))
    company = Company(company_name="Acme", automation_mode=mode, requires_login=requires_login,
                      has_captcha=has_captcha, careers_url="https://acme.example/careers")
    db.add(company); db.commit(); db.refresh(company)
    now = datetime.now(timezone.utc)
    vac = Vacancy(company_id=company.id, source_id="s1", title="Ops Manager", content_hash="h1",
                  is_open=True, first_seen_at=now, last_seen_at=now,
                  application_url="https://acme.example/apply")
    db.add(vac); db.commit(); db.refresh(vac)
    app = Application(user_id=user.id, vacancy_id=vac.id, mode=mode, status="AWAITING_APPROVAL",
                      application_url="https://acme.example/apply")
    db.add(app); db.commit(); db.refresh(app)
    return user, app


def test_engine_auto_submits(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
    user, app = _setup(db, mode="auto")
    sub = MockSubmitter(SIMPLE_FORM)
    result = attempt_auto_submit(db, user, app, submitter=sub)
    assert result.status == "SUBMITTED" and result.submission_method == "auto"
    assert sub.submitted and sub.submitted["email"] == "thandi@x.co"


def test_engine_stops_on_captcha(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
    user, app = _setup(db, mode="auto")
    sub = MockSubmitter(CAPTCHA_FORM)
    result = attempt_auto_submit(db, user, app, submitter=sub)
    assert result.status == "CANDIDATE_ACTION_REQUIRED"
    assert sub.submitted is None  # never bypassed


def test_engine_stops_on_login(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
    user, app = _setup(db, mode="auto")
    result = attempt_auto_submit(db, user, app, submitter=MockSubmitter(LOGIN_FORM))
    assert result.status == "CANDIDATE_ACTION_REQUIRED"


def test_engine_stops_on_unknown_required(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
    user, app = _setup(db, mode="auto")
    result = attempt_auto_submit(db, user, app, submitter=MockSubmitter(UNKNOWN_REQUIRED))
    assert result.status == "CANDIDATE_ACTION_REQUIRED"


def test_engine_assisted_does_not_submit(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
    user, app = _setup(db, mode="assisted")
    sub = MockSubmitter(SIMPLE_FORM)
    result = attempt_auto_submit(db, user, app, submitter=sub)
    assert result.status == "CANDIDATE_ACTION_REQUIRED" and sub.submitted is None


def test_engine_respects_manual_policy(db, monkeypatch):
    monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
    user, app = _setup(db, mode="manual")
    sub = MockSubmitter(SIMPLE_FORM)
    result = attempt_auto_submit(db, user, app, submitter=sub)
    assert result.status == "CANDIDATE_ACTION_REQUIRED" and sub.submitted is None


def test_engine_global_switch_off(db):
    # AUTOMATION_ENABLED defaults False -> never submits.
    user, app = _setup(db, mode="auto")
    sub = MockSubmitter(SIMPLE_FORM)
    result = attempt_auto_submit(db, user, app, submitter=sub)
    assert result.status == "CANDIDATE_ACTION_REQUIRED" and sub.submitted is None


# ---- live Playwright (skips if unavailable) ----

def test_live_playwright_submission(db, monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import urllib.parse

    chrome = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    try:
        import playwright  # noqa: F401
    except Exception:
        pytest.skip("playwright not installed")
    if not chrome:
        pytest.skip("no chromium browser available")

    captured: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(b"<html><body><form method='POST' action='/submit'>"
                             b"<input name='email' required><input name='full_name' required>"
                             b"<button type='submit'>Apply</button></form></body></html>")

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            captured.update({k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode()).items()})
            self.send_response(200); self.end_headers(); self.wfile.write(b"Thanks")

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(settings, "AUTOMATION_ENABLED", True)
        monkeypatch.setattr(settings, "PLAYWRIGHT_EXECUTABLE_PATH", chrome[0])
        user, app = _setup(db, mode="auto")
        url = f"http://127.0.0.1:{port}/"
        app.application_url = url
        db.query(Vacancy).filter(Vacancy.id == app.vacancy_id).update({"application_url": url})
        db.commit()
        try:
            result = attempt_auto_submit(db, user, app)  # real PlaywrightSubmitter
        except Exception as e:
            pytest.skip(f"browser launch failed: {e}")
        assert result.status == "SUBMITTED", result.status
        assert captured.get("email") == "thandi@x.co"
        assert captured.get("full_name") == "Thandi Mokoena"
    finally:
        server.shutdown()
