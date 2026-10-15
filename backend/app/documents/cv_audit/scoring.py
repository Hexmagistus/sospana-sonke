"""Phase 1 & 5 scoring — five areas, each with the reasons behind the number.

This is an informed, rule-based assessment (every deduction is listed in
``basis``), NOT a rating from any ATS vendor, and it cannot guarantee that a
CV passes a particular ATS or earns an interview. The same functions score the
original CV and the rebuilt one, so the before/after comparison is fair.
"""
from __future__ import annotations

import re

from app.documents.cv_audit.rewrite import BASE_OF, domain_evidence

AREA_LABELS = {
    "ats_compatibility": "ATS compatibility",
    "content_quality": "Content quality",
    "keyword_relevance": "Keyword relevance",
    "professional_presentation": "Professional presentation",
    "recruitment_effectiveness": "Recruitment effectiveness",
}
WEIGHTS = {"ats_compatibility": 0.25, "content_quality": 0.2, "keyword_relevance": 0.15,
           "professional_presentation": 0.2, "recruitment_effectiveness": 0.2}

CLICHES = ["hardworking", "hard-working", "hard working", "team player", "go-getter", "self-motivated",
           "self motivated", "results-driven", "results driven", "dynamic individual", "passionate about",
           "dedicated and", "think outside the box", "detail-oriented individual", "fast learner",
           "quick learner", "works well under pressure", "challenging position", "where i can grow",
           "use my skills", "seeking a challenging"]
WEAK = ["responsible for", "duties included", "duties include", "tasked with", "in charge of", "helped with",
        "worked on", "involved in", "my job was", "duties consisted of"]
_NUMBER = re.compile(r"\b\d[\d,.]*\s?(?:%|percent|ml|l\b|kl|ml/d|m³|tons?|tonnes?|hours?|hrs|days?|staff|people|"
                     r"operators|employees|samples|units|sites|plants|r\s?\d)|\br\s?\d[\d ,.]*|\b\d{2,}\b", re.I)


def _clamp(x: float) -> int:
    return int(max(0, min(100, round(x))))


def date_formats(text: str) -> int:
    pats = [r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?:19|20)\d{2}",
            r"\b\d{1,2}/(?:19|20)\d{2}\b", r"\b(?:19|20)\d{2}/\d{1,2}\b", r"\b\d{1,2}\.(?:19|20)\d{2}\b"]
    return sum(1 for p in pats if re.search(p, text, re.I))


def view_from_parsed(parsed: dict, text: str, findings: list[dict]) -> dict:
    bullets = [b for e in parsed.get("experience", []) for b in e.get("bullets", [])]
    return {
        "name": parsed.get("full_name"), "email": parsed.get("email"), "phone": parsed.get("phone"),
        "headline": parsed.get("headline"), "summary": parsed.get("summary") or "",
        "headings": parsed.get("headings", []), "skills": parsed.get("skills", []),
        "experience": parsed.get("experience", []), "education": parsed.get("education", []),
        "certifications": parsed.get("certifications", []), "bullets": bullets,
        "sensitive": parsed.get("sensitive", []), "references": len(parsed.get("references", [])),
        "findings": findings, "text": text, "date_formats": date_formats(text), "parsed": parsed,
        "rebuilt": False,
    }


def view_from_rebuilt(cv: dict, text: str, findings: list[dict], parsed: dict) -> dict:
    bullets = [b for e in cv.get("experience", []) for b in e.get("bullets", [])]
    skills = [t for ts in (cv.get("competencies") or {}).values() for t in ts] + list(cv.get("software", []))
    from app.documents.cv_audit.render import sections
    return {
        "name": cv.get("full_name"), "email": cv.get("email"), "phone": cv.get("phone"),
        "headline": cv.get("headline"), "summary": cv.get("summary") or "",
        "headings": [{"text": s["title"], "canonical": "standard"} for s in sections(cv)],
        "skills": skills, "experience": cv.get("experience", []),
        "education": (cv.get("education", []) + cv.get("current_studies", [])),
        "certifications": cv.get("certifications", []), "bullets": bullets,
        "sensitive": [], "references": len(cv.get("references") or []), "findings": findings, "text": text,
        "date_formats": date_formats(text), "parsed": parsed, "rebuilt": True,
    }


def _ats(v: dict) -> tuple[int, list[str]]:
    score, basis = 100.0, []
    for f in v["findings"]:
        if f.get("area") != "ats":
            continue
        d = {"high": 15, "medium": 8, "low": 3}.get(f["severity"], 3)
        score -= d
        basis.append(f"−{d}: {f['message']}")
    nonstd = [h for h in v["headings"] if h["canonical"] in ("_other", "personal", "declaration",
                                                             "contact")]
    if nonstd:
        d = min(12, 4 * len(nonstd))
        score -= d
        basis.append(f"−{d}: non-standard or outdated section headings ({', '.join(h['text'] for h in nonstd[:4])}).")
    canon = {h["canonical"] for h in v["headings"]}
    if not v["rebuilt"]:
        for sec, label in (("experience", "work experience"), ("education", "education"), ("skills", "skills")):
            if sec not in canon:
                score -= 8
                basis.append(f"−8: no clearly headed {label} section an ATS can anchor on.")
    if not v["email"]:
        score -= 15
        basis.append("−15: no email address could be extracted.")
    if not v["phone"]:
        score -= 8
        basis.append("−8: no phone number could be extracted.")
    if not v["name"]:
        score -= 10
        basis.append("−10: the candidate name could not be identified at the top of the document.")
    undated = [e for e in v["experience"] if not e.get("start")]
    if undated:
        d = min(12, 4 * len(undated))
        score -= d
        basis.append(f"−{d}: {len(undated)} role(s) without readable employment dates.")
    unresolved = [e for e in v["experience"] if not (e.get("position") and e.get("employer"))]
    if unresolved:
        d = min(12, 4 * len(unresolved))
        score -= d
        basis.append(f"−{d}: {len(unresolved)} role(s) where job title and employer cannot be told apart.")
    if not basis:
        basis.append("No parsing risks detected: single column, standard headings, contact details in the body.")
    return _clamp(score), basis


def _content(v: dict) -> tuple[int, list[str]]:
    score, basis = 100.0, []
    summary = (v["summary"] or "").lower()
    if not summary:
        score -= 15
        basis.append("−15: no professional summary.")
    else:
        hits = [c for c in CLICHES if c in summary]
        if hits:
            d = min(20, 7 * len(hits))
            score -= d
            basis.append(f"−{d}: summary relies on clichés ({', '.join(hits[:3])}) rather than evidence.")
    blob = " ".join(v["bullets"]).lower()
    weak = sum(blob.count(w) for w in WEAK)
    if weak:
        d = min(18, 4 * weak)
        score -= d
        basis.append(f"−{d}: {weak} passive phrase(s) such as “responsible for”.")
    fp = len(re.findall(r"(?:^|\. |\n)i\s", " ".join(v["bullets"] + [v["summary"]]).lower()))
    if fp:
        d = min(10, 3 * fp)
        score -= d
        basis.append(f"−{d}: first-person wording (“I…”).")
    thin = [e for e in v["experience"] if len(e.get("bullets", [])) < 2]
    if thin:
        d = min(15, 5 * len(thin))
        score -= d
        basis.append(f"−{d}: {len(thin)} role(s) with fewer than two descriptive points.")
    if v["sensitive"]:
        d = min(12, 3 * len(v["sensitive"]))
        score -= d
        basis.append(f"−{d}: unnecessary personal data ({', '.join(s['label'] for s in v['sensitive'][:4])}).")
    if not v["experience"]:
        score -= 20
        basis.append("−20: no work experience entries could be identified.")
    if not basis:
        basis.append("Clear, specific content with no clichés, passive phrasing or unnecessary personal data.")
    return _clamp(score), basis


def _keywords(v: dict) -> tuple[int, list[str]]:
    basis = []
    domains = domain_evidence(v["parsed"]) if not v["rebuilt"] else domain_evidence({
        "summary": v["summary"], "skills": v["skills"], "experience": v["experience"],
        "education": v["education"], "certifications": v["certifications"]})
    strong = [d for d, n in domains if n >= 6]
    score = 45 + min(30, 10 * len(strong))
    basis.append(f"+{min(30, 10 * len(strong))}: {len(strong)} professional domain(s) clearly evidenced"
                 + (f" ({', '.join(strong[:3])})." if strong else "."))
    bullets_blob = " ".join(v["bullets"]).lower()
    skills = [s for s in v["skills"] if len(s) > 2]
    if skills:
        def demonstrated(skill: str) -> bool:
            core = skill.lower().split(" (")[0]
            if core in bullets_blob:
                return True
            stems = [w[:6] for w in re.findall(r"[a-z]{5,}", core)]
            return bool(stems) and all(st in bullets_blob for st in stems[:2])
        in_context = [s for s in skills if demonstrated(s)]
        ratio = len(in_context) / len(skills)
        add = round(15 * ratio)
        score += add
        basis.append(f"+{add}: {len(in_context)} of {len(skills)} listed skills are also demonstrated in your experience.")
    else:
        basis.append("+0: no skills section to match against.")
    text = " ".join(v["text"].split())
    acr = {a.rstrip("s") for a in re.findall(r"\b(SOPs?|GMP|GLP|OHS|SHEQ|SCADA|PLCs?|HACCP|LIMS|PPE|HAZOP|KPIs?)\b", text)}
    expanded = [a for a in acr if re.search(r"\(" + a + r"s?\)", text)]
    if acr and len(expanded) < len(acr):
        basis.append("+0: some acronyms never appear in full, so searches for the spelt-out term can miss them.")
    else:
        score += 10
        basis.append("+10: technical acronyms are also written in full where they first appear.")
    basis.append("General industry keywords only — no job advert was supplied, so this is not vacancy-specific.")
    return _clamp(score), basis


def _presentation(v: dict) -> tuple[int, list[str]]:
    score, basis = 100.0, []
    for f in v["findings"]:
        if f.get("area") != "presentation" and f.get("code") not in ("graphics",):
            continue
        d = {"high": 15, "medium": 8, "low": 4}.get(f["severity"], 4)
        score -= d
        basis.append(f"−{d}: {f['message']}")
    if v["date_formats"] > 1:
        score -= 6
        basis.append(f"−6: {v['date_formats']} different date formats are mixed.")
    if not v["headline"]:
        score -= 8
        basis.append("−8: no professional headline under the name.")
    if v["sensitive"]:
        score -= 6
        basis.append("−6: a personal-details block takes prime space at the top of the CV.")
    long_bullets = [b for b in v["bullets"] if len(b.split()) > 32]
    if long_bullets:
        score -= min(8, 2 * len(long_bullets))
        basis.append(f"−{min(8, 2 * len(long_bullets))}: {len(long_bullets)} bullet point(s) run longer than two lines.")
    if not basis:
        basis.append("Consistent, single-column layout with clear hierarchy, uniform dates and no distracting graphics.")
    return _clamp(score), basis


def _effectiveness(v: dict) -> tuple[int, list[str]]:
    score, basis = 30.0, []
    if v["headline"]:
        score += 10
        basis.append("+10: a headline states your professional identity at a glance.")
    summary = v["summary"] or ""
    if summary and not any(c in summary.lower() for c in CLICHES) and len(summary.split()) >= 25:
        score += 12
        basis.append("+12: the summary names your role, employers, qualifications and strengths.")
    elif summary:
        score += 4
        basis.append("+4: a summary exists but is generic.")
    bullets = v["bullets"]
    if bullets:
        verb_starts = sum(1 for b in bullets if b.split()[0].lower().strip(",") in BASE_OF)
        r = verb_starts / len(bullets)
        add = round(14 * r)
        score += add
        basis.append(f"+{add}: {verb_starts} of {len(bullets)} bullet points open with a clear action verb.")
        quantified = sum(1 for b in bullets if _NUMBER.search(b))
        add = min(20, round(40 * quantified / len(bullets)))
        score += add
        basis.append(f"+{add}: {quantified} of {len(bullets)} bullet points carry a verified figure or outcome"
                     + (" — add real numbers where you can evidence them." if quantified < len(bullets) / 3 else "."))
    if v["references"] >= 2:
        score += 4
        basis.append(f"+4: {v['references']} referees listed, as South African employers expect.")
    else:
        basis.append("+0: fewer than two referees listed — South African employers usually expect two or three.")
    dated = [e for e in v["experience"] if e.get("start")]
    if v["experience"] and len(dated) == len(v["experience"]):
        score += 6
        basis.append("+6: every role is dated, so career progression is easy to follow.")
    edu = v["education"]
    unclear = [e for e in edu if e.get("status") == "unverified"]
    if edu and not unclear:
        score += 4
        basis.append("+4: qualification status (completed / in progress) is clear.")
    elif unclear:
        basis.append(f"+0: {len(unclear)} qualification(s) have no clear completion date or status.")
    return _clamp(score), basis


def score_view(v: dict) -> dict:
    fns = {"ats_compatibility": _ats, "content_quality": _content, "keyword_relevance": _keywords,
           "professional_presentation": _presentation, "recruitment_effectiveness": _effectiveness}
    areas = {}
    for key, fn in fns.items():
        s, basis = fn(v)
        areas[key] = {"label": AREA_LABELS[key], "score": s, "basis": basis}
    overall = _clamp(sum(areas[k]["score"] * w for k, w in WEIGHTS.items()))
    return {"overall": overall, "areas": areas,
            "disclaimer": "An informed, rule-based assessment by Sospana Sonke — not an official rating from any "
                          "ATS vendor. No CV is guaranteed to pass every ATS or to secure an interview."}
