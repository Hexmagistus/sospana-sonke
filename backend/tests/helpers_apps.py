"""Test helpers: job matching is gone, so an application is created directly in the DB
(there is no API route that prepares one from a match any more)."""
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from app.applications.answers import generate_standard_answers
from app.models.application import Application, ApplicationAnswer, ApplicationEvent
from app.models.company import Company
from app.models.vacancy import Vacancy


def seed_vacancy(db_engine, title="Operations Manager"):
    s = sessionmaker(bind=db_engine)()
    try:
        c = Company(company_name="Acme Logistics", sector="Logistics",
                    careers_url="https://boards.greenhouse.io/acme")
        s.add(c); s.commit(); s.refresh(c)
        now = datetime.now(timezone.utc)
        v = Vacancy(company_id=c.id, source_id="s1", title=title, location="Johannesburg",
                    description="SQL and Excel needed.", application_url="https://apply.example.com/1",
                    content_hash="h-" + title, is_open=True, first_seen_at=now, last_seen_at=now)
        s.add(v); s.commit(); s.refresh(v)
        return v.id
    finally:
        s.close()


def make_application(client, tokens, db_engine, *, title="Operations Manager", status="AWAITING_APPROVAL"):
    """A prepared application for the logged-in user; returns its id."""
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    vac_id = seed_vacancy(db_engine, title=title)
    s = sessionmaker(bind=db_engine)()
    try:
        app = Application(user_id=me["id"], vacancy_id=vac_id, mode="approval", status=status,
                          application_url="https://apply.example.com/1")
        s.add(app); s.flush()
        facts = {"years_experience": 6, "work_authorization": "South African citizen"}
        for a in generate_standard_answers(facts, "Acme Logistics", title):
            s.add(ApplicationAnswer(application_id=app.id, **a))
        s.add(ApplicationEvent(application_id=app.id, event_type="prepared", actor="system",
                               status_to=status, detail="Prepared in 'approval' mode."))
        s.commit()
        return app.id
    finally:
        s.close()
