"""Job-Aligned CV Builder routes: analyse a pasted job advert, get a
transparent match report + fact-check, generate the tailored CV / cover
letter / interview prep, and track the application afterwards.

Complements (does not replace) the scraped-vacancy flow in routes_matches.py
and routes_documents.py — this is for a job the candidate found themselves
(an ad, a referral, LinkedIn) rather than one Sospana Sonke discovered.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.documents.render import list_templates
from app.models.job_analysis import JobAnalysis
from app.models.user import User
from app.schemas.document import CVVersionResponse, CoverLetterResponse
from app.schemas.interview import InterviewPrepResponse
from app.schemas.job_analysis import (
    AnalyzeJobRequest, AnalyzeJobResult, JobAnalysisResponse, JobAnalysisDetailResponse,
    FactCheck, GenerateCvRequest, TrackerUpdateRequest, TemplateInfo,
)
from app.services import job_analysis_service as svc

router = APIRouter(prefix="/tailor", tags=["tailor"])


@router.get("/templates", response_model=list[TemplateInfo])
def get_templates():
    return list_templates()


@router.post("/analyze", response_model=AnalyzeJobResult, status_code=status.HTTP_201_CREATED)
def analyze(body: AnalyzeJobRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    analysis, draft_cv, violations = svc.analyze_job(
        db, user, body.job_title, body.company_name, body.job_description,
    )
    return AnalyzeJobResult(
        job_analysis=JobAnalysisDetailResponse.model_validate(analysis),
        draft_cv=draft_cv,
        fact_check=FactCheck(ok=not violations, violations=violations),
    )


@router.post("/{job_analysis_id}/generate-cv", response_model=CVVersionResponse,
             status_code=status.HTTP_201_CREATED)
def generate_cv(job_analysis_id: str, body: GenerateCvRequest, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    version = svc.generate_cv(db, user, job_analysis_id, body.cv_data, body.template)
    return CVVersionResponse.model_validate(version)


@router.post("/{job_analysis_id}/generate-cover-letter", response_model=CoverLetterResponse,
             status_code=status.HTTP_201_CREATED)
def generate_cover_letter(job_analysis_id: str, db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    letter = svc.generate_cover_letter(db, user, job_analysis_id)
    return CoverLetterResponse.model_validate(letter)


@router.post("/{job_analysis_id}/interview-prep", response_model=InterviewPrepResponse,
             status_code=status.HTTP_201_CREATED)
def generate_interview_prep(job_analysis_id: str, db: Session = Depends(get_db),
                            user: User = Depends(get_current_user)):
    from app.services.interview_service import generate_interview_prep_for_job
    prep = generate_interview_prep_for_job(db, user, job_analysis_id)
    return InterviewPrepResponse.model_validate(prep)


@router.get("/{job_analysis_id}/interview-prep")
def get_interview_prep(job_analysis_id: str, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    from app.models.interview import InterviewPrep
    svc.get_job_analysis(db, user, job_analysis_id)  # ownership check, 404s if not the user's
    rows = (db.query(InterviewPrep)
            .filter(InterviewPrep.user_id == user.id, InterviewPrep.match_id.is_(None))
            .order_by(InterviewPrep.created_at.desc()).all())
    for prep in rows:
        if (prep.content or {}).get("job_analysis_id") == job_analysis_id:
            return InterviewPrepResponse.model_validate(prep)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No interview prep yet.")


@router.get("/applications", response_model=list[JobAnalysisResponse])
def list_applications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [JobAnalysisResponse.model_validate(a) for a in svc.list_job_analyses(db, user)]


@router.get("/applications/{job_analysis_id}", response_model=JobAnalysisDetailResponse)
def get_application(job_analysis_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    return JobAnalysisDetailResponse.model_validate(svc.get_job_analysis(db, user, job_analysis_id))


@router.put("/applications/{job_analysis_id}", response_model=JobAnalysisDetailResponse)
def update_application(job_analysis_id: str, body: TrackerUpdateRequest, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    analysis = svc.update_tracker(db, user, job_analysis_id, body.status, body.notes, body.date_applied)
    return JobAnalysisDetailResponse.model_validate(analysis)


@router.delete("/applications/{job_analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(job_analysis_id: str, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    svc.delete_job_analysis(db, user, job_analysis_id)
