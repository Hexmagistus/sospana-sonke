"""Interview-prep generation (blueprint Phase 2) for a job the candidate pasted.

Deterministic and truthful: questions come from the job's own requirements and the
talking points and watch-outs from that job's analysis. (Prep per stored job match
was removed with job matching.)
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.interview import InterviewPrep
from app.models.job_analysis import JobAnalysis
from app.models.user import User

_GENERAL_TIPS = [
    "Research the company: its products, recent news, and values.",
    "Use the STAR method (Situation, Task, Action, Result) for behavioural questions.",
    "Prepare two or three thoughtful questions to ask the interviewer.",
    "Be truthful about your experience — never overstate it.",
    "Have concrete examples ready that show impact and numbers where possible.",
]


def generate_interview_prep_for_job(db: Session, user: User, job_analysis_id: str) -> InterviewPrep:
    """Interview prep for a candidate-pasted job (no scraped Vacancy/match) —
    built the same way, from real data the candidate already has: the job's
    own requirements (for questions) and this job analysis's own Match Report
    (for talking points and watch-outs). Never invents a false experience for
    the candidate to claim in interview."""
    analysis = db.get(JobAnalysis, job_analysis_id)
    if analysis is None or analysis.user_id != user.id or analysis.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

    title = analysis.job_title or "this role"
    company_name = analysis.company_name or "the company"
    requirements = (analysis.extracted or {}).get("requirements") or []

    questions = [
        f"Why are you interested in the {title} role at {company_name}?",
        "Walk us through the experience that makes you a good fit for this position.",
        "What are your key strengths, and where are you working to develop?",
        "Describe a challenge you faced at work and how you handled it (use STAR).",
        "Where do you see yourself growing in this role?",
    ]
    for r in [r for r in requirements if r.get("kind") == "hard"][:6]:
        questions.append(f"This role requires: “{r['text']}”. How do you meet it?")
    for r in [r for r in requirements if r.get("kind") == "soft"][:4]:
        questions.append(f"The role values “{r['text']}”. Can you speak to your experience there?")

    talking_points = [m["text"] for m in (analysis.strong_matches or [])][:8] or [
        "Emphasise the experience that aligns with the role."]
    watch_outs = [f"Be ready to address: {m['text']}" for m in
                 [*(analysis.missing_requirements or []), *(analysis.partial_matches or [])]][:8]

    content = {
        "vacancy_title": title, "company_name": company_name, "questions": questions,
        "talking_points": talking_points, "watch_outs": watch_outs, "tips": _GENERAL_TIPS,
        "job_analysis_id": analysis.id,
    }
    prep = InterviewPrep(user_id=user.id, match_id=None, vacancy_id=None,
                         content=content, generated_by="deterministic")
    db.add(prep)
    db.commit()
    db.refresh(prep)
    return prep
