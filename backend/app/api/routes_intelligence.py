"""Public natural-language search over stored roles and the employer directory.

The parser is deterministic. Nothing is sent to a language model. The response
never includes an advert body, employer research notes, or a candidate record.
A successful search may add one anonymous daily total. The question is not written.
"""
import logging
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.intelligence import IntelligenceSearchResponse, IntelligenceUnderstood
from app.schemas.usage import UsageScorecardResponse
from app.services.intelligence_search import answer_question
from app.services.usage_counts import (
    classify_search,
    privacy_opt_out,
    record_click,
    record_search,
    scorecard,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

class ClickIn(BaseModel):
    target: Literal["employer", "vacancy"]
    id: str = Field(min_length=36, max_length=36)

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        return value.strip()


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
    if not privacy_opt_out(request):
        try:
            record_search(db, classify_search(answer))
        except Exception:
            logger.exception("anonymous search total was not stored")
            db.rollback()
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


@router.post("/clicks", status_code=204)
@limiter.limit("30/minute")
def count_outbound_click(request: Request, body: ClickIn, db: Session = Depends(get_db)):
    """Count one outbound click for an employer or a role. No account and no question."""
    if privacy_opt_out(request):
        return Response(status_code=204)
    record_click(db, body.target, body.id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/admin/scorecard", response_model=UsageScorecardResponse)
@limiter.limit("60/minute")
def usage_scorecard(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    days: int = Query(default=7, ge=1, le=90),
):
    """Search success, empty answers, clicks, and source links for the UTC window."""
    response.headers["Cache-Control"] = "private, no-store"
    return scorecard(db, days)
