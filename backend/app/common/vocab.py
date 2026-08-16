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
