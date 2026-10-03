"""Daily Spark: read the member's streak, and record the day they revealed it.

Opt-in by interaction only: nothing here sends a notification or email, and the
only write is the member pressing "Reveal today's spark".
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services.spark_service import record_open, sast_today, spark_status

router = APIRouter(prefix="/spark", tags=["spark"])


class SparkStatus(BaseModel):
    today: str
    opened_today: bool
    current_streak: int
    longest_streak: int
    total_opens: int


@router.get("/status", response_model=SparkStatus)
def get_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return spark_status(db, user.id, sast_today())


@router.post("/open", response_model=SparkStatus)
@limiter.limit("30/hour")
def open_today(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return record_open(db, user.id, sast_today())
