"""Deterministic, offline CV structuring (default provider).

This does NOT call any external AI service, so it is free and always available.
It extracts only what it can reliably identify from the text (contact details,
links, known skills, languages, and education/experience lines under recognised
headings). It never fabricates. It is deliberately conservative: the candidate
confirms everything before it is treated as fact. A hosted model (ClaudeProvider)
can be enabled for richer extraction, but the truthfulness contract is identical.
"""
from __future__ import annotations

import re

from app.ai.base import AIProvider, StructuredCV
from app.common.vocab import SKILLS_BY_CATEGORY as _SKILLS, LANGUAGES as _LANGUAGES

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+27|0)\s?(?:\d[\s-]?){8,10}\d")
_LINKEDIN = re.compile(r"https?://(?:www\.)?linkedin\.com/[^\s)]+", re.I)
_GITHUB = re.compile(r"https?://(?:www\.)?github\.com/[^\s)]+", re.I)
_URL = re.compile(r"https?://[^\s)]+", re.I)

_EDU_HINTS = ["university", "college", "institute", "polytechnic", "tvet", "school of",
              "bachelor", "b.sc", "bsc", "b.com", "bcom", "diploma", "national diploma",
              "honours", "master", "m.sc", "msc", "mba", "matric", "grade 12", "certificate", "degree"]

_EXP_HEADINGS = ["experience", "employment", "work history", "professional experience", "career history"]
_EDU_HEADINGS = ["education", "qualifications", "academic", "training"]


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _sections(lines: list[str]) -> dict[str, list[str]]:
    """Group lines under the last-seen recognised heading."""
    out: dict[str, list[str]] = {"_": []}
    current = "_"
    for ln in lines:
        low = ln.lower().strip(" :")
        if any(low == h or low.startswith(h) for h in _EXP_HEADINGS):
            current = "experience"; out.setdefault(current, []); continue
        if any(low == h or low.startswith(h) for h in _EDU_HEADINGS):
            current = "education"; out.setdefault(current, []); continue
        # A short all-caps or title line that isn't a heading resets nothing.
        out.setdefault(current, []).append(ln)
    return out


class HeuristicProvider(AIProvider):
    name = "heuristic"

    def structure_cv(self, text: str) -> StructuredCV:
        lines = _lines(text)
        low_text = text.lower()
        result: StructuredCV = {}

        # Contact
        if m := _EMAIL.search(text):
            result["email"] = m.group(0)
        if m := _PHONE.search(text):
            result["phone"] = re.sub(r"\s+", "", m.group(0))
        if m := _LINKEDIN.search(text):
            result["linkedin_url"] = m.group(0).rstrip(".,")
        if m := _GITHUB.search(text):
            result["github_url"] = m.group(0).rstrip(".,")
        # A portfolio = first non-linkedin/github url
        for u in _URL.findall(text):
            u = u.rstrip(".,")
            if "linkedin.com" not in u and "github.com" not in u:
                result["portfolio_url"] = u
                break

        # Name: first non-empty line that is not contact info and looks like a name.
        for ln in lines[:5]:
            if _EMAIL.search(ln) or _URL.search(ln) or _PHONE.search(ln):
                continue
            words = ln.split()
            if 1 < len(words) <= 4 and all(w[0].isupper() for w in words if w[:1].isalpha()):
                result["full_name"] = ln
                break

        # Skills (dictionary match, deduped, preserves category)
        skills: list[dict] = []
        seen = set()
        for category, terms in _SKILLS.items():
            for term in terms:
                if re.search(r"\b" + re.escape(term) + r"\b", low_text) and term not in seen:
                    seen.add(term)
                    skills.append({"name": term.title(), "category": category})
        if skills:
            result["skills"] = skills

        # Languages
        langs = []
        for lang in _LANGUAGES:
            if re.search(r"\b" + re.escape(lang) + r"\b", low_text):
                canonical = lang.replace("isi", "").replace("se", "").title() if lang.startswith(("isi", "se")) else lang.title()
                if canonical not in langs:
                    langs.append(canonical)
        if langs:
            result["languages"] = langs

        sections = _sections(lines)

        # Education: lines containing an education hint
        education = []
        edu_candidates = sections.get("education", []) + [ln for ln in lines if any(h in ln.lower() for h in _EDU_HINTS)]
        seen_edu = set()
        for ln in edu_candidates:
            if any(h in ln.lower() for h in _EDU_HINTS) and ln not in seen_edu:
                seen_edu.add(ln)
                education.append({"institution": ln, "qualification": None,
                                  "field_of_study": None, "level": None})
            if len(education) >= 8:
                break
        if education:
            result["education"] = education

        # Work experience: lines under an experience heading with an employer/role shape.
        experience = []
        for ln in sections.get("experience", []):
            # crude "Role at Employer" or "Employer — Role" detection
            if re.search(r"\bat\b|—|–|\|", ln) and len(ln) < 160:
                experience.append({"employer": ln, "position": None,
                                   "responsibilities": None, "technologies": []})
            if len(experience) >= 12:
                break
        if experience:
            result["work_experience"] = experience

        return result
