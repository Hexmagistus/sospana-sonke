"""Candidate profile and its child tables (blueprint sections 3, 4 & 9).

A profile is 1:1 with a user. Education, certifications, work experience, and
skills are child records. Every child carries `confirmed_by_candidate`: data
extracted from an uploaded CV by the AI is stored with this set to False, so the
system can always distinguish AI-suggested data from candidate-verified fact
(this is central to the truthfulness guarantee).
"""
from datetime import date

from sqlalchemy import String, Boolean, Integer, Text, Date, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin


class CandidateProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    # Personal
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), default="South Africa", nullable=True)
    work_authorization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(20), nullable=True)  # email | sms | phone

    # Career
    current_occupation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    desired_occupations: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    industries: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_locations: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    work_mode_preference: Mapped[str | None] = mapped_column(String(20), nullable=True)  # remote|hybrid|onsite|any
    minimum_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)            # monthly ZAR
    willing_to_relocate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Other
    languages: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    drivers_licence: Mapped[str | None] = mapped_column(String(40), nullable=True)
    professional_memberships: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    education: Mapped[list["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    work_experience: Mapped[list["WorkExperience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class _ChildBase(UUIDMixin, TimestampMixin):
    confirmed_by_candidate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)  # manual | cv_extraction


class Education(_ChildBase, Base):
    __tablename__ = "education"
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    qualification: Mapped[str | None] = mapped_column(String(200), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(200), nullable=True)
    level: Mapped[str | None] = mapped_column(String(80), nullable=True)  # e.g. Degree, Diploma, Matric
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile: Mapped["CandidateProfile"] = relationship(back_populates="education")


class Certification(_ChildBase, Base):
    __tablename__ = "certifications"
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile: Mapped["CandidateProfile"] = relationship(back_populates="certifications")


class WorkExperience(_ChildBase, Base):
    __tablename__ = "work_experience"
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employer: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    profile: Mapped["CandidateProfile"] = relationship(back_populates="work_experience")


class Skill(_ChildBase, Base):
    __tablename__ = "skills"
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)  # technical|software|soft|management|other
    profile: Mapped["CandidateProfile"] = relationship(back_populates="skills")
