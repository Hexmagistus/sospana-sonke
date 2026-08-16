"""Interview-prep generation (blueprint Phase 2).

Deterministic and truthful: builds questions from the vacancy's real requirements,
talking points from the match's own reasons, and watch-outs from its gaps. An AI
provider could later rephrase, but the substance comes from stored match data.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.interview import InterviewPrep
from app.models.match import CandidateMatch
from app.models.user import User
from app.models.vacancy import Vacancy, VacancyRequirement

_GENERAL_TIPS = [
    "Research the company: its products, recent news, and values.",
    "Use the STAR method (Situation, Task, Action, Result) for behavioural questions.",
    "Prepare two or three thoughtful questions to ask the interviewer.",
    "Be truthful about your experience — never overstate it.",
    "Have concrete examples ready that show impact and numbers where possible.",
]


def generate_interview_prep(db: Session, user: User, match_id: str) -> InterviewPrep:
    match = db.get(CandidateMatch, match_id)
    if match is None or match.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    vac = db.get(Vacancy, match.vacancy_id)
    company = db.get(Company, vac.company_id) if vac else None
    reqs = (db.query(VacancyRequirement)
            .filter(VacancyRequirement.vacancy_id == match.vacancy_id).all()) if vac else []

    title = vac.title if vac else "this role"
    company_name = company.company_name if company else "the company"

    questions = [
        f"Why are you interested in the {title} role at {company_name}?",
        "Walk us through the experience that makes you a good fit for this position.",
        "What are your key strengths, and where are you working to develop?",
        "Describe a challenge you faced at work and how you handled it (use STAR).",
        "Where do you see yourself growing in this role?",
    ]
    for r in [r for r in reqs if r.kind == "hard"][:6]:
        questions.append(f"This role requires: “{r.text}”. How do you meet it?")
    for r in [r for r in reqs if r.kind == "soft"][:4]:
        questions.append(f"The role values “{r.text}”. Can you speak to your experience there?")

    talking_points = list(match.reasons or []) or ["Emphasise the experience that aligns with the role."]
    watch_outs = [f"Be ready to address: {g}" for g in (match.gaps or [])]

    content = {
        "vacancy_title": title,
        "company_name": company_name,
        "questions": questions,
        "talking_points": talking_points,
        "watch_outs": watch_outs,
        "tips": _GENERAL_TIPS,
    }
    prep = InterviewPrep(user_id=user.id, match_id=match.id, vacancy_id=match.vacancy_id,
                         content=content, generated_by="deterministic")
    db.add(prep)
    db.commit()
    db.refresh(prep)
    return prep
