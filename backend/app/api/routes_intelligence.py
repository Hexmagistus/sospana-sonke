"""Public natural-language search over stored roles and the employer directory.

The parser is deterministic. Nothing is sent to a language model. The response
never includes an advert body, employer research notes, or a candidate record.
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.intelligence import IntelligenceSearchResponse, IntelligenceUnderstood
from app.services.intelligence_search import answer_question

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


def _understood(answer) -> IntelligenceUnderstood:
    data = asdict(answer.understood)
    data.pop("source_types", None)
    data.pop("declined", None)
    data.pop("prompt", None)
    data.pop("supported", None)
    return IntelligenceUnderstood(**data)


@router.get("/search", response_model=IntelligenceSearchResponse)
@limiter.limit("30/minute")
def search_intelligence(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    q: str = Query(default="", max_length=200, description="A question about stored roles or employers"),
):
    """Answer one question from rows we already hold. No sign-in. Not cached: the question may name a person."""
    response.headers["Cache-Control"] = "no-store"
    answer = answer_question(db, q)
    return IntelligenceSearchResponse(
        question=answer.question,
        understood=_understood(answer),
        llm=answer.llm,
        enough_data=answer.enough_data,
        summary=answer.summary,
        reading=answer.reading,
        limitations=answer.limitations,
        follow_ups=answer.follow_ups,
        vacancies=answer.vacancies,
        vacancy_count=answer.vacancy_count,
        employers=answer.employers,
        employer_count=answer.employer_count,
        with_link_count=answer.with_link_count,
        counted_at=answer.counted_at,
    )
