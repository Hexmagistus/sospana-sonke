"""Shared vocabularies used by CV extraction and matching.

Kept in one place so extraction and matching agree on what counts as a skill or
language. In production this is data-driven (a table the admin can grow); here it
is a curated starter set biased toward the South African market.
"""
from __future__ import annotations

SKILLS_BY_CATEGORY: dict[str, list[str]] = {
    "technical": ["python", "java", "javascript", "typescript", "c++", "c#", "sql", "html", "css",
                  "react", "node", "django", "fastapi", "flask", "spring", "aws", "azure", "gcp",
                  "docker", "kubernetes", "linux", "git", "rest", "graphql", "postgresql", "mysql",
                  "mongodb", "power bi", "tableau", "machine learning", "data analysis"],
    "software": ["excel", "word", "powerpoint", "sap", "salesforce", "sage", "pastel", "quickbooks",
                 "autocad", "ms project", "jira", "confluence"],
    "management": ["project management", "team leadership", "budgeting", "stakeholder management",
                   "operations management", "supply chain", "procurement", "scheduling"],
    "operational": ["logistics", "warehouse", "inventory", "production planning", "quality control",
                    "maintenance", "health and safety", "iso"],
    "soft": ["communication", "problem solving", "teamwork", "time management", "leadership",
             "attention to detail", "adaptability", "customer service"],
}

# Flattened set of all known skill terms.
SKILL_TERMS: set[str] = {term for terms in SKILLS_BY_CATEGORY.values() for term in terms}

LANGUAGES: list[str] = ["english", "afrikaans", "zulu", "isizulu", "xhosa", "isixhosa", "sotho",
                        "sesotho", "tswana", "setswana", "venda", "tsonga", "swati", "ndebele",
                        "french", "portuguese"]

# Education level ranking (higher number = higher level), used for qualification matching.
EDUCATION_RANK: dict[str, int] = {
    "matric": 1, "grade 12": 1, "certificate": 2, "diploma": 3, "national diploma": 3,
    "degree": 4, "bachelor": 4, "bcom": 4, "bsc": 4, "b.com": 4, "b.sc": 4,
    "honours": 5, "postgraduate": 5, "master": 6, "mba": 6, "msc": 6, "phd": 7, "doctorate": 7,
}

# ---- CV Builder / job-description analysis vocab (Sospana Sonke CV module) --

# Strong resume action verbs. Used to (a) detect action verbs already present in
# a pasted job advert, for keyword-alignment guidance, and (b) reward a
# candidate's own experience bullets in the CV quality scorer when they already
# start with one of these. We never insert these into a candidate's CV text —
# they are only used to recognise and score wording the candidate supplied.
ACTION_VERBS: list[str] = [
    "achieved", "managed", "led", "developed", "implemented", "coordinated", "delivered",
    "improved", "increased", "reduced", "streamlined", "designed", "built", "created",
    "launched", "negotiated", "supervised", "trained", "mentored", "analysed", "analyzed",
    "resolved", "optimised", "optimized", "planned", "executed", "monitored", "maintained",
    "operated", "controlled", "audited", "inspected", "scheduled", "budgeted", "forecasted",
    "administered", "facilitated", "collaborated", "oversaw", "directed", "established",
    "generated", "reported", "presented", "researched", "investigated", "compiled",
    "processed", "handled", "supported", "assisted", "conducted", "performed",
]

# Phrases that read as weak/passive resume language. Penalised (lightly, never
# rejected) by the CV quality scorer's "Professional Language" sub-score, purely
# as wording guidance — never a reason to alter the candidate's factual content.
WEAK_RESUME_PHRASES: list[str] = [
    "responsible for", "duties included", "was tasked with", "in charge of",
    "helped with", "worked on", "involved in", "assisted with", "my job was",
    "i was responsible", "tasked with", "duties consisted of",
]

# Seniority signal words, ordered loosely from junior to executive. Used by the
# job-description parser to guess a role's seniority level from its own wording
# (never inferred about the candidate — only about the vacancy text).
SENIORITY_SIGNALS: dict[str, list[str]] = {
    "Graduate / Entry-level": ["graduate", "internship", "intern", "trainee", "entry level",
                               "entry-level", "junior", "no experience necessary"],
    "Mid-level": ["mid-level", "mid level", "intermediate"],
    "Senior": ["senior", "experienced", "specialist", "advanced"],
    "Managerial": ["manager", "supervisor", "team lead", "team leader", "head of department"],
    "Executive / Leadership": ["director", "executive", "head of", "chief", "vp ", "vice president",
                               "general manager", "ceo", "coo", "cfo", "cto", "president"],
}

# Additional requirement categories the job-description parser recognises beyond
# the ones used for scraped vacancies (app/scraper/extract.py): a pasted advert
# often includes duty/responsibility bullets and named-industry references that
# the matching engine treats as "other" (unassessable) but which the CV builder
# still wants to show back to the candidate for transparency.
RESPONSIBILITY_HINTS: list[str] = [
    "manage", "oversee", "coordinate", "supervise", "prepare", "maintain", "monitor",
    "ensure", "conduct", "perform", "handle", "process", "operate", "assist", "support",
    "liaise", "compile", "report to", "administer", "schedule", "plan and", "responsible for",
]

INDUSTRY_TERMS: list[str] = [
    "manufacturing", "mining", "fmcg", "retail", "logistics", "supply chain", "banking",
    "financial services", "insurance", "telecommunications", "healthcare", "pharmaceutical",
    "agriculture", "construction", "engineering", "energy", "oil and gas", "water",
    "wastewater", "chemical", "automotive", "hospitality", "education", "public sector",
    "government", "municipal", "non-profit", "ngo", "information technology", "ecommerce",
    "e-commerce", "media", "food and beverage", "packaging", "textiles", "renewable energy",
]
