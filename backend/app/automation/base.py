"""Shared types and the Submitter interface for the automation engine."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DetectedBlockers:
    captcha: bool = False
    login_required: bool = False
    mfa_required: bool = False
    file_upload_required: bool = False
    no_form: bool = False

    @property
    def blocking(self) -> bool:
        return any([self.captcha, self.login_required, self.mfa_required,
                    self.file_upload_required, self.no_form])

    def reasons(self) -> list[str]:
        out = []
        if self.captcha:
            out.append("CAPTCHA present — cannot be bypassed; candidate must complete it.")
        if self.login_required:
            out.append("Login required — please sign in on the employer site and submit.")
        if self.mfa_required:
            out.append("Multi-factor verification required — candidate must complete it.")
        if self.file_upload_required:
            out.append("The form requires a file upload — please attach your CV and submit.")
        if self.no_form:
            out.append("No application form was detected on the page.")
        return out


@dataclass
class FormFieldSpec:
    name: str
    input_type: str = "text"
    label: str | None = None
    required: bool = False


@dataclass
class SubmissionPlan:
    values: dict[str, str] = field(default_factory=dict)   # field name -> truthful value
    unknown_required: list[str] = field(default_factory=list)


@dataclass
class SubmissionResult:
    status: str                # submitted | action_required | failed
    reason: str | None = None
    filled: dict | None = None


class Submitter(ABC):
    """Loads a page and (when permitted) fills + submits a form."""

    @abstractmethod
    def load(self, url: str) -> str: ...

    @abstractmethod
    def fill_and_submit(self, url: str, values: dict[str, str]) -> SubmissionResult: ...
