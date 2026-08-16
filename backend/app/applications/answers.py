"""Deterministic application-answer generation (blueprint section 15).

Factual questions are answered ONLY from the candidate's confirmed profile. When
the profile does not contain the answer, we return `UNKNOWN — CANDIDATE INPUT
REQUIRED` rather than guessing. A motivational question ("why do you want to work
here?") may be drafted from verified facts and is marked source=ai_generated.
"""
from __future__ import annotations

UNKNOWN = "UNKNOWN — CANDIDATE INPUT REQUIRED"


def _answer(question, value, source="profile"):
    if value in (None, "", []):
        return {"question": question, "answer": UNKNOWN, "source": "profile", "is_unknown": True}
    return {"question": question, "answer": str(value), "source": source, "is_unknown": False}


def generate_standard_answers(facts: dict, company_name: str | None, vacancy_title: str | None) -> list[dict]:
    answers: list[dict] = []

    # Work authorisation — factual, from profile only.
    answers.append(_answer("Are you legally authorised to work in South Africa?",
                           facts.get("work_authorization")))

    # Driver's licence — present => Yes; absent => UNKNOWN (absence is not a 'No').
    lic = facts.get("drivers_licence")
    answers.append({"question": "Do you have a valid driver's licence?",
                    "answer": f"Yes ({lic})" if lic else UNKNOWN,
                    "source": "profile", "is_unknown": not bool(lic)})

    # Years of experience — factual.
    answers.append(_answer("How many years of relevant experience do you have?",
                           facts.get("years_experience")))

    # Expected salary — factual (candidate's stated minimum).
    answers.append(_answer("What is your expected monthly salary (ZAR)?",
                           facts.get("minimum_salary")))

    # Willingness to relocate — tri-state.
    relo = facts.get("willing_to_relocate")
    if relo is None:
        answers.append({"question": "Are you willing to relocate?", "answer": UNKNOWN,
                        "source": "profile", "is_unknown": True})
    else:
        answers.append({"question": "Are you willing to relocate?",
                        "answer": "Yes" if relo else "No", "source": "profile", "is_unknown": False})

    # Notice period — not in profile; always candidate input.
    answers.append({"question": "What is your notice period?", "answer": UNKNOWN,
                    "source": "profile", "is_unknown": True})

    # Motivational — may be drafted from verified facts (not a factual claim).
    company = company_name or "your organisation"
    role = vacancy_title or "this role"
    current = facts.get("current_occupation")
    industries = facts.get("industries") or []
    basis = f"my background as a {current}" if current else "my experience"
    if industries:
        basis += f" in {industries[0]}"
    motivation = (f"I am keen to bring {basis} to {company} in the {role} position, where I can "
                  f"contribute to your team while continuing to grow professionally.")
    answers.append({"question": f"Why do you want to work at {company}?",
                    "answer": motivation, "source": "ai_generated", "is_unknown": False})

    return answers
