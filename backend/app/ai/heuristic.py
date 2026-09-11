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
_OTHER_HEADINGS = ["skills", "languages", "certifications", "references", "profile", "summary",
                   "objective", "personal details", "contact", "curriculum vitae", "resume", "cv"]

# Only an EXPLICIT statement counts — never computed from date ranges, which
# would be an estimate presented as fact.
_YEARS_EXPERIENCE = re.compile(
    r"(\d{1,2})\+?\s*years?\s*(?:of\s*)?(?:relevant\s*|professional\s*|working\s*|work\s*)?experience", re.I
)
_TITLE_LABEL = re.compile(r"^(?:current\s+)?(?:job\s+)?title\s*[:\-]\s*(.+)$", re.I)
_LOCATION_LABEL = re.compile(r"^(?:location|city|address|based\s+in)\s*[:\-]\s*(.+)$", re.I)
_CITY_LINE = re.compile(r"^([A-Z][a-zA-Z'\-]+(?:\s[A-Z][a-zA-Z'\-]+){0,2}),\s*([A-Za-z .]+)$")


def _split_role_line(line: str) -> tuple[str | None, str | None]:
    """'Operations Supervisor at Acme Logistics' -> (position, employer). Only the
    unambiguous ' at ' pattern is split — a dash or pipe separator is left as one
    unsplit line rather than guessing which side is the role and which the employer."""
    m = re.search(r"^(.+?)\s+\bat\b\s+(.+)$", line, re.I)
    if m:
        return m.group(1).strip(" -–—|"), m.group(2).strip(" -–—|")
    return None, line.strip(" -–—|")


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
                position, employer = _split_role_line(ln)
                experience.append({"employer": employer, "position": position,
                                   "responsibilities": None, "technologies": []})
            if len(experience) >= 12:
                break
        if experience:
            result["work_experience"] = experience

        # Years of experience — only ever from an explicit statement in the text.
        if m := _YEARS_EXPERIENCE.search(text):
            result["years_experience"] = int(m.group(1))

        # Current occupation: prefer the position of the most recent (first-listed,
        # assuming reverse-chronological order) role, then an explicit "Title:" label,
        # then a short title-like line directly under the candidate's name.
        occupation = None
        for exp in experience:
            if exp.get("position"):
                occupation = exp["position"]
                break
        if not occupation:
            for ln in lines[:8]:
                if m := _TITLE_LABEL.match(ln):
                    occupation = m.group(1).strip()
                    break
        if not occupation and result.get("full_name") in lines:
            name_idx = lines.index(result["full_name"])
            if name_idx + 1 < len(lines):
                candidate = lines[name_idx + 1].strip()
                words = candidate.split()
                low_candidate = candidate.lower().strip(" :")
                is_heading = any(low_candidate == h or low_candidate.startswith(h)
                                 for h in _EXP_HEADINGS + _EDU_HEADINGS + _OTHER_HEADINGS)
                if (1 < len(words) <= 6 and not candidate.isupper() and not is_heading
                        and not _EMAIL.search(candidate) and not _URL.search(candidate)
                        and not _PHONE.search(candidate)):
                    occupation = candidate
        if occupation:
            result["current_occupation"] = occupation

        # City: an explicit label first, then a plain "City, Region/Country" line
        # near the top of the document (where contact/header details usually sit).
        city = None
        for ln in lines[:8]:
            if m := _LOCATION_LABEL.match(ln):
                city = m.group(1).split(",")[0].strip()
                break
        if not city:
            for ln in lines[:8]:
                if (_EMAIL.search(ln) or _URL.search(ln) or _PHONE.search(ln)
                        or ln == result.get("full_name")):
                    continue
                if m := _CITY_LINE.match(ln):
                    city = m.group(1).strip()
                    break
        if city:
            result["city"] = city

        return result
