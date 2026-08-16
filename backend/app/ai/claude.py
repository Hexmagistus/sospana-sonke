"""Claude-backed CV structuring (optional, enabled via config).

Enabled with AI_PROVIDER=claude and ANTHROPIC_API_KEY set. Uses a cheap model by
default (cost control, blueprint section 37) and a strict JSON-only,
never-fabricate instruction. If the call fails, the caller falls back to the
heuristic provider so the feature degrades gracefully rather than breaking.
"""
from __future__ import annotations

import json

import httpx

from app.ai.base import AIProvider, StructuredCV
from app.core.config import settings

_SYSTEM = (
    "You extract structured data from a CV. Return ONLY valid JSON matching the "
    "requested schema. NEVER invent, infer, or embellish information that is not "
    "explicitly present in the CV text. If a field is not present, omit it or use null. "
    "Do not add skills, employers, qualifications, or dates that are not written in the text."
)

_SCHEMA_HINT = (
    'Return JSON with keys: full_name, email, phone, linkedin_url, github_url, '
    'portfolio_url, skills (list of {name, category}), languages (list of strings), '
    'education (list of {institution, qualification, field_of_study, level}), '
    'work_experience (list of {employer, position, responsibilities, technologies}), '
    'certifications (list of {name, issuing_organization}).'
)

_MODEL_MAP = {"claude-haiku": "claude-3-5-haiku-latest", "claude-sonnet": "claude-3-5-sonnet-latest"}


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        self._model = _MODEL_MAP.get(settings.AI_MODEL, settings.AI_MODEL)

    def structure_cv(self, text: str) -> StructuredCV:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": 2000,
                "system": _SYSTEM,
                "messages": [{
                    "role": "user",
                    "content": f"{_SCHEMA_HINT}\n\nCV TEXT:\n{text[:20000]}",
                }],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"]
        # Be tolerant of the model wrapping JSON in prose/code fences.
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            return {}
        return json.loads(content[start:end + 1])
