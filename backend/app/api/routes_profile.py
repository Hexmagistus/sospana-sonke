"""Candidate profile CRUD (blueprint Step 2).

Every endpoint is scoped to the authenticated user: a candidate can only ever
read or modify their own profile and child records (security, section 15).
"""
from typing import Type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.profile import Education, Certification, WorkExperience, Skill
from app.schemas.profile import (
    ProfileUpdate, ProfileResponse,
    EducationCreate, EducationResponse,
    CertificationCreate, CertificationResponse,
    WorkExperienceCreate, WorkExperienceResponse,
    SkillCreate, SkillResponse,
)
from app.services.profile_service import get_or_create_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ProfileResponse.model_validate(get_or_create_profile(db, user.id))


@router.put("", response_model=ProfileResponse)
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = get_or_create_profile(db, user.id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return ProfileResponse.model_validate(profile)


def _register_child_crud(model: Type[Base], create_schema: Type[BaseModel],
                         response_schema: Type[BaseModel], path: str, tag_name: str):
    """Attach list/create/update/delete for a profile child model, ownership-scoped."""

    @router.get(f"/{path}", response_model=list[response_schema], name=f"list_{path}")
    def _list(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        profile = get_or_create_profile(db, user.id)
        rows = db.query(model).filter(model.profile_id == profile.id).all()
        return [response_schema.model_validate(r) for r in rows]

    @router.post(f"/{path}", response_model=response_schema, status_code=status.HTTP_201_CREATED,
                 name=f"create_{path}")
    def _create(body: create_schema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):  # type: ignore
        profile = get_or_create_profile(db, user.id)
        row = model(profile_id=profile.id, confirmed_by_candidate=True, source="manual",
                    **body.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return response_schema.model_validate(row)

    @router.put(f"/{path}/{{item_id}}", response_model=response_schema, name=f"update_{path}")
    def _update(item_id: str, body: create_schema, db: Session = Depends(get_db),  # type: ignore
                user: User = Depends(get_current_user)):
        profile = get_or_create_profile(db, user.id)
        row = db.get(model, item_id)
        if row is None or row.profile_id != profile.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        for field, value in body.model_dump().items():
            setattr(row, field, value)
        # An edit by the candidate counts as confirmation of that record.
        row.confirmed_by_candidate = True
        db.commit()
        db.refresh(row)
        return response_schema.model_validate(row)

    @router.delete(f"/{path}/{{item_id}}", status_code=status.HTTP_204_NO_CONTENT, name=f"delete_{path}")
    def _delete(item_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        profile = get_or_create_profile(db, user.id)
        row = db.get(model, item_id)
        if row is None or row.profile_id != profile.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        db.delete(row)
        db.commit()


_register_child_crud(Education, EducationCreate, EducationResponse, "education", "education")
_register_child_crud(Certification, CertificationCreate, CertificationResponse, "certifications", "certifications")
_register_child_crud(WorkExperience, WorkExperienceCreate, WorkExperienceResponse, "experience", "experience")
_register_child_crud(Skill, SkillCreate, SkillResponse, "skills", "skills")
