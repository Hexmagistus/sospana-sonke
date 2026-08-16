"""Cover-letter drafting (blueprint section 12).

Deterministic, truthful default: assembles a concise, professional letter from the
candidate's real profile and the vacancy. Avoids generic AI-sounding filler. A
hosted-AI variant can be enabled later behind the same interface, but its output is
still passed through truthfulness validation.
"""
from __future__ import annotations


def build_cover_letter(facts: dict, company_name: str | None, vacancy_title: str | None) -> str:
    name = facts.get("full_name") or "The candidate"
    role = vacancy_title or "the advertised role"
    company = company_name or "your organisation"
    years = facts.get("years_experience")
    industries = facts.get("industries") or []
    skills = facts.get("skills") or []
    current = facts.get("current_occupation")

    opening = f"Dear Hiring Team,\n\nI am writing to apply for the {role} position at {company}."

    cred_bits = []
    if current:
        cred_bits.append(f"I currently work as a {current}")
    if years:
        cred_bits.append(f"and bring {years} year{'s' if years != 1 else ''} of experience")
    if industries:
        cred_bits.append(f"in {', '.join(industries[:2])}")
    credibility = (" ".join(cred_bits) + ".") if cred_bits else ""

    strengths = ""
    if skills:
        top = ", ".join(skills[:5])
        strengths = (f" My relevant strengths include {top}, which align with the requirements "
                     f"of this role.")

    body = (f"{credibility}{strengths}").strip()
    if body:
        body = "\n\n" + body

    closing = ("\n\nI would welcome the opportunity to discuss how my background fits your needs. "
               "Thank you for considering my application.\n\nYours sincerely,\n" + name)

    return opening + body + closing
