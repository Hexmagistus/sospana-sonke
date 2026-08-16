"""Model registry. Import all models here so metadata is complete."""
from app.models.user import User  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.profile import (  # noqa: F401
    CandidateProfile, Education, Certification, WorkExperience, Skill,
)
from app.models.cv import CV  # noqa: F401
from app.models.vacancy import VacancySource, Vacancy, VacancyRequirement  # noqa: F401
from app.models.match import CandidateMatch, SystemSetting  # noqa: F401
from app.models.document import CVVersion, CoverLetter  # noqa: F401
from app.models.application import (  # noqa: F401
    ApplicationSettings, Application, ApplicationAnswer, ApplicationEvent,
)
from app.models.subscription import Subscription, Payment  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.notification import Notification, JobRun, PushToken  # noqa: F401
from app.models.interview import InterviewPrep  # noqa: F401
