"""In-memory Submitter for tests (no browser). Records what it would submit."""
from __future__ import annotations

from app.automation.base import Submitter, SubmissionResult


class MockSubmitter(Submitter):
    def __init__(self, html: str, fail: bool = False) -> None:
        self._html = html
        self._fail = fail
        self.submitted: dict | None = None

    def load(self, url: str) -> str:
        return self._html

    def fill_and_submit(self, url: str, values: dict[str, str]) -> SubmissionResult:
        if self._fail:
            return SubmissionResult("failed", reason="Simulated submission failure.")
        self.submitted = dict(values)
        return SubmissionResult("submitted", filled=dict(values))
