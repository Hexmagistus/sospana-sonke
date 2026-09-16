"""Career Explorer: qualification -> adjacent career families (blueprint section 19).

A small, curated, hand-maintained taxonomy -- not a machine-learned model and not
scraped from anywhere. Each entry is deliberately qualitative (career titles a
qualification commonly leads to, no salary figures, no fabricated statistics).
This is the same kind of "adjacent role family" idea the Career Agent already
uses for logged-in candidates browsing by current occupation
(`frontend/src/app/agent/page.tsx`'s `ROLE_FAMILIES`) but keyed off a
*qualification* instead, and owned on the backend so it's one source of truth
other features (skills search, career pathways) can grow from later.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CareerFamily:
    label: str                 # the qualification family, e.g. "Biotechnology / Microbiology"
    keywords: list[str]        # matched case-insensitively as substrings
    related_careers: list[str]
    note: str                  # one honest, qualitative line -- no salary/stat claims


CAREER_FAMILIES: list[CareerFamily] = [
    CareerFamily(
        label="Biotechnology / Microbiology",
        keywords=["biotechnology", "microbiology", "biotech", "life sciences"],
        related_careers=[
            "Laboratory Technician", "Microbiology Technician", "Quality Control Technician",
            "Water Treatment / Process Controller", "Production Technician", "Environmental Officer",
            "Food Safety Officer",
        ],
        note="Lab-trained graduates are commonly hired across water treatment, food/beverage "
             "production, and pharmaceutical/quality-control roles, not only pure research labs.",
    ),
    CareerFamily(
        label="Water & Wastewater Treatment",
        keywords=["water treatment", "wastewater", "water care", "water and wastewater",
                  "water process"],
        related_careers=[
            "Process Controller", "Water Quality Officer", "Plant Operator",
            "Environmental Compliance Officer", "Laboratory Technician", "Operations Supervisor",
        ],
        note="Municipal water boards, industrial plants, and mines all run their own water/"
             "effluent treatment operations and hire for this skill set directly.",
    ),
    CareerFamily(
        label="Chemical / Process Operations",
        keywords=["chemical operations", "process control", "process operator", "chemical plant"],
        related_careers=[
            "Process Controller", "Plant Operator", "Production Supervisor",
            "Quality Controller", "Maintenance Planner", "SHEQ Officer",
        ],
        note="Skills transfer directly across chemicals, water treatment, food/beverage, and "
             "mineral-processing plants -- the equipment differs, the control-room discipline doesn't.",
    ),
    CareerFamily(
        label="Engineering (Mechanical / Electrical / Civil)",
        keywords=["mechanical engineering", "electrical engineering", "civil engineering",
                  "engineering technician", "technologist"],
        related_careers=[
            "Engineering Technician", "Maintenance Engineer", "Site Supervisor",
            "Project Engineer", "Quality Assurance Engineer", "Health & Safety Officer",
        ],
        note="An engineering qualification opens both hands-on plant/site roles and "
             "office-based project/QA roles -- worth deciding which you'd rather target.",
    ),
    CareerFamily(
        label="Information Technology",
        keywords=["information technology", "computer science", "software", "it ", "informatics"],
        related_careers=[
            "Software Developer", "IT Support Technician", "Systems Administrator",
            "Data Analyst", "Database Administrator", "QA / Test Analyst",
        ],
        note="Entry-level IT roles (support/helpdesk) are usually the fastest way in; "
             "developer/analyst roles typically want a portfolio or internship experience too.",
    ),
    CareerFamily(
        label="Business / Operations Management",
        keywords=["operations management", "business management", "business administration"],
        related_careers=[
            "Operations Supervisor", "Operations Manager", "Production Planner",
            "Project Coordinator", "Business Analyst", "Supply Chain Coordinator",
        ],
        note="This qualification is generalist by design -- it's read as a signal for "
             "coordination/supervision roles across almost any industry.",
    ),
    CareerFamily(
        label="Finance / Accounting",
        keywords=["accounting", "finance", "bcom", "bookkeeping", "financial management"],
        related_careers=[
            "Bookkeeper", "Accounts Clerk", "Creditors / Debtors Clerk",
            "Financial Officer", "Payroll Administrator", "Junior Accountant",
        ],
        note="Most finance-department hiring starts at clerk level with SAICA/SAIPA "
             "articles or further study as the route to a full accounting designation.",
    ),
    CareerFamily(
        label="Human Resources",
        keywords=["human resources", "hr management", "industrial psychology"],
        related_careers=[
            "HR Administrator", "Recruitment Officer", "Payroll Administrator",
            "Training Coordinator", "Employee Relations Officer", "HR Generalist",
        ],
        note="Larger employers (SOEs, municipalities, big private firms) are the most "
             "common entry point for a first HR administration role.",
    ),
    CareerFamily(
        label="Health Sciences",
        keywords=["nursing", "health sciences", "public health", "environmental health",
                  "occupational health"],
        related_careers=[
            "Staff Nurse", "Environmental Health Practitioner", "Occupational Health Nurse",
            "Health Promoter", "Clinical Technician",
        ],
        note="Many of these roles require professional council registration (e.g. SANC) "
             "on top of the qualification itself -- check the specific listing's requirements.",
    ),
    CareerFamily(
        label="Education",
        keywords=["education", "teaching", "pgce"],
        related_careers=[
            "Teacher", "Teaching Assistant", "Tutor", "Training Facilitator",
            "Curriculum Developer", "Education Officer (NGO/government)",
        ],
        note="SACE registration is generally required to teach at a public school -- "
             "corporate/NGO training roles don't require it.",
    ),
    CareerFamily(
        label="Agriculture",
        keywords=["agriculture", "agricultural science", "agronomy", "animal science"],
        related_careers=[
            "Agricultural Technician", "Farm Manager", "Extension Officer",
            "Quality Controller (agri-processing)", "Laboratory Technician",
        ],
        note="Agri-processing plants (food, beverage) hire agriculture graduates into "
             "quality-control and production roles as often as farms do.",
    ),
    CareerFamily(
        label="Logistics / Supply Chain",
        keywords=["logistics", "supply chain", "procurement", "transport management"],
        related_careers=[
            "Logistics Coordinator", "Warehouse Supervisor", "Procurement Officer",
            "Inventory Controller", "Fleet Controller", "Supply Chain Analyst",
        ],
        note="Manufacturing, retail, and mining all run large logistics operations -- "
             "the qualification is portable across all three.",
    ),
    CareerFamily(
        label="Safety, Health, Environment & Quality (SHEQ)",
        keywords=["safety management", "sheq", "occupational health and safety", "samtrac"],
        related_careers=[
            "SHEQ Officer", "Safety Officer", "Environmental Officer",
            "Quality Assurance Officer", "Risk Officer",
        ],
        note="Almost every industrial employer (mining, manufacturing, construction, "
             "water) has a standing SHEQ function -- one of the more portable specialisations.",
    ),
    CareerFamily(
        label="Marketing / Communications",
        keywords=["marketing", "communications", "public relations", "journalism"],
        related_careers=[
            "Marketing Coordinator", "Communications Officer", "Social Media Coordinator",
            "Content Creator", "Public Relations Officer",
        ],
        note="A portfolio of real work (even self-directed) tends to matter as much as "
             "the qualification for entry-level marketing/comms roles.",
    ),
    CareerFamily(
        label="Artisan / Trades",
        keywords=["millwright", "fitter", "electrician trade", "boilermaker", "artisan",
                  "trade test"],
        related_careers=[
            "Artisan (specific trade)", "Maintenance Technician", "Plant Fitter",
            "Electrical Technician", "Maintenance Planner",
        ],
        note="A completed trade test is usually the actual hiring gate here, more than "
             "the underlying qualification alone -- worth checking a listing's exact wording.",
    ),
    CareerFamily(
        label="General / Matric only",
        keywords=["matric", "grade 12", "no formal qualification"],
        related_careers=[
            "General Worker", "Admin Clerk", "Data Capturer", "Call Centre Agent",
            "Learnership / Internship programmes", "Security Officer",
        ],
        note="Learnerships and internships are usually the most realistic route from "
             "matric-only into a structured career path -- look for those specifically.",
    ),
]


def find_career_families(text: str, limit: int = 2) -> list[CareerFamily]:
    """Best-effort match of free text (a qualification name, field of study, or
    current occupation) against the taxonomy above. Returns [] rather than a
    guess when nothing recognisable is found."""
    if not text:
        return []
    low = text.lower()
    matches = [fam for fam in CAREER_FAMILIES if any(kw in low for kw in fam.keywords)]
    return matches[:limit]
