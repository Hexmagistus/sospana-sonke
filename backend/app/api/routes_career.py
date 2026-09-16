"""Career Explorer route (blueprint section 19).

Turns a qualification (given directly, or inferred from the candidate's own
profile/registration answers) into adjacent career families, each backed by a
live count of currently-open vacancies with a matching title -- never a fake
number, and 0 is shown honestly rather than hidden.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.profile import CandidateProfile, Education
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.career import CareerExplorerResponse, CareerFamilyResponse, CareerOption
from app.services.career_taxonomy import find_career_families

router = APIRouter(tags=["career"])


def _default_basis(db: Session, user: User) -> str | None:
    """Best-effort qualification/occupation text to explore from, when the
    caller doesn't supply one directly. Never fabricated -- returns the
    candidate's own stated data, or None."""
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    if profile:
        for e in db.query(Education).filter(Education.profile_id == profile.id).all():
            text = " ".join(x for x in [e.qualification, e.field_of_study] if x)
            if text.strip():
                return text
        if profile.current_occupation:
            return profile.current_occupation
    if user.qualification_name:
        return user.qualification_name
    if user.preferred_position:
        return user.preferred_position
    return None


def _open_vacancy_count(db: Session, title: str) -> int:
    return (db.query(Vacancy)
            .filter(Vacancy.is_open.is_(True), Vacancy.deleted_at.is_(None),
                    Vacancy.title.ilike(f"%{title}%"))
            .count())


@router.get("/career-explorer", response_model=CareerExplorerResponse)
def explore_careers(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                    qualification: str | None = Query(
                        default=None,
                        description="A qualification, field of study, or occupation to explore from. "
                                    "Defaults to the candidate's own profile/registration answers.")):
    basis = qualification or _default_basis(db, user)
    if not basis:
        return CareerExplorerResponse(based_on=None, families=[])

    families = find_career_families(basis)
    matched_keyword = basis.lower()
    out = []
    for fam in families:
        hit = next((kw for kw in fam.keywords if kw in matched_keyword), fam.keywords[0])
        out.append(CareerFamilyResponse(
            label=fam.label,
            matched_on=hit,
            related_careers=[
                CareerOption(title=title, open_vacancies=_open_vacancy_count(db, title))
                for title in fam.related_careers
            ],
            note=fam.note,
        ))
    return CareerExplorerResponse(based_on=basis, families=out)
