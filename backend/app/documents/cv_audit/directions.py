"""Phase 7 — up to three career directions the CV's own evidence supports, plus
the outstanding-information checklist (Deliverable 4).

Directions are suggestions to consider, ranked purely by how much of the
candidate's own text supports them. Credentials listed are common options in
the South African market for that path — the candidate should check any
specific vacancy's requirements; none are presented as required.
"""
from __future__ import annotations

import re
from datetime import date

from app.documents.cv_audit.rewrite import domain_evidence

CATALOGUE = [
    {
        "id": "water_operations", "group": "Water and Wastewater Treatment",
        "title": "Water and wastewater treatment operations (process control and supervision)",
        "emphasise": ["Treatment-process duties in your current/most recent role", "Water quality sampling and analysis",
                      "Process control qualifications and classification", "Safety and compliance on shift"],
        "credentials": ["A recognised Water and Wastewater Process Control qualification (NQF levels 2–5)",
                        "Confirmation of your process controller classification under the Water Services Act "
                        "regulations, if you hold one",
                        "Membership of the Water Institute of Southern Africa (WISA)"],
        "targeted": "Useful: lead with treatment-process competencies and put water-sector roles first.",
    },
    {
        "id": "process_control", "group": "Process Operations and Control",
        "title": "Process control in chemical, manufacturing or processing plants",
        "emphasise": ["Plant operation and control-room/SCADA work", "SOP adherence and shift handovers",
                      "Troubleshooting and equipment-fault reporting", "Chemical operations training"],
        "credentials": ["National Certificate: Chemical Operations (CHIETA) or equivalent, if not already held",
                        "Lean or Six Sigma Yellow/Green Belt", "Membership of SAIChE (South African Institution of "
                        "Chemical Engineers) at an eligible grade"],
        "targeted": "Useful: foreground plant types, control systems and production environments.",
    },
    {
        "id": "laboratory_qc", "group": "Laboratory and Microbiology",
        "title": "Laboratory, quality control and microbiology roles",
        "emphasise": ["Laboratory and microbiological testing experience", "GLP/GMP compliance",
                      "Biotechnology or science qualifications", "Sample handling and instrument care"],
        "credentials": ["Registration with SACNASP (South African Council for Natural Scientific Professions) "
                        "in an eligible category", "ISO/IEC 17025 laboratory quality awareness training",
                        "Good Laboratory Practice (GLP) refresher certificate"],
        "targeted": "Useful: move laboratory roles and science qualifications higher.",
    },
    {
        "id": "quality_compliance", "group": "Quality Assurance and Compliance",
        "title": "Quality assurance and compliance",
        "emphasise": ["Quality checks, specifications and SOPs", "Audit, inspection and non-conformance work",
                      "GMP/GLP and regulatory compliance"],
        "credentials": ["ISO 9001 internal auditor certificate", "HACCP or FSSC 22000 (food and beverage plants)",
                        "Root-cause analysis / CAPA training"],
        "targeted": "Useful: lead with quality systems and audit experience.",
    },
    {
        "id": "operations_management", "group": "Operations Management and Continuous Improvement",
        "title": "Operations, production or shift management",
        "emphasise": ["Operations management qualifications", "Scheduling, KPIs and performance monitoring",
                      "Training others and coordinating teams", "Continuous-improvement examples with verified results"],
        "credentials": ["Lean Six Sigma Green Belt", "A project management certificate (e.g. PMI CAPM/PMP or PRINCE2)",
                        "Supervisory or management development programme"],
        "targeted": "Useful: lead with management qualifications and any supervision or improvement outcomes.",
    },
    {
        "id": "sheq", "group": "Occupational Health and Safety",
        "title": "Safety, health, environment and quality (SHEQ) roles",
        "emphasise": ["Incident reporting and safety participation", "Risk assessment and inspections",
                      "Legal compliance (OHS Act) and SOPs"],
        "credentials": ["SAMTRAC (NOSA) or an equivalent occupational health and safety qualification",
                        "First Aid, fire-fighting and incident-investigation certificates",
                        "SACPCMP registration (for construction health and safety roles)"],
        "targeted": "Useful: group all safety evidence and certificates together near the top.",
    },
    {
        "id": "maintenance", "group": "Maintenance Coordination and Equipment Reliability",
        "title": "Maintenance planning and equipment reliability",
        "emphasise": ["Equipment monitoring and fault reporting", "Coordination with artisans and maintenance teams",
                      "Use of maintenance systems (e.g. SAP PM)"],
        "credentials": ["Maintenance planning certificate", "SAP Plant Maintenance (PM) end-user training"],
        "targeted": "Optional: only if you want to move toward planning and reliability work.",
    },
]

_BIOTECH = {
    "id": "biotechnology", "title": "Biotechnology and bioprocessing",
    "emphasise": ["Biotechnology qualification", "Fermentation, microbiology or bioprocess work",
                  "Laboratory techniques and data recording"],
    "credentials": ["SACNASP registration in an eligible category", "Postgraduate study in biotechnology or "
                    "bioprocess engineering"],
    "targeted": "Useful: lead with science qualifications and laboratory experience.",
}


def career_directions(cv: dict) -> list[dict]:
    evidence = dict(domain_evidence(cv))
    text = " ".join([cv.get("summary") or "", " ".join(cv.get("skills", [])),
                     " ".join(b for e in cv.get("experience", []) for b in e.get("bullets", [])),
                     " ".join(e.get("position") or "" for e in cv.get("experience", [])),
                     " ".join(e.get("qualification") or "" for e in cv.get("education", []))]).lower()
    ranked = []
    for d in CATALOGUE:
        score = evidence.get(d["group"], 0)
        if d["id"] == "operations_management" and "operations management" in text:
            score += 6
        if score >= 3:
            ranked.append((score, d))
    if re.search(r"biotechnolog|bioprocess|fermentation", text):
        ranked.append((evidence.get("Laboratory and Microbiology", 0) - 1, _BIOTECH))
    ranked.sort(key=lambda x: -x[0])

    out = []
    for score, d in ranked[:3]:
        why = _why(d, cv)
        out.append({"id": d["id"], "title": d["title"], "why": why, "emphasise": d["emphasise"],
                    "credentials": d["credentials"], "targeted_cv": d["targeted"], "evidence_score": score})
    return out


def _why(d: dict, cv: dict) -> str:
    bits = []
    for e in cv.get("experience", []):
        pos = e.get("position") or ""
        blob = (pos + " " + " ".join(e.get("bullets", []))).lower()
        keys = {
            "water_operations": r"water|sedimentation|filter|turbidity|dosing|chlorin",
            "process_control": r"process|plant|scada|operat",
            "laboratory_qc": r"laborator|microbio|sample|culture|test",
            "quality_compliance": r"quality|glp|gmp|sop|audit|inspect|complian",
            "operations_management": r"manag|supervis|train|schedul|kpi",
            "sheq": r"safety|ohs|incident|risk|hazard",
            "maintenance": r"maintenance|equipment|fault|repair",
            "biotechnology": r"microbio|biotech|culture|ferment",
        }.get(d["id"], r"$^")
        if re.search(keys, blob) and pos:
            bits.append(f"{pos}{' at ' + e['employer'] if e.get('employer') else ''}")
    quals = [e.get("qualification") for e in cv.get("education", [])
             if e.get("qualification") and re.search(
                 {"operations_management": r"operations|management", "laboratory_qc": r"biotech|science|chem",
                  "biotechnology": r"biotech", "water_operations": r"water", "process_control": r"chemical|process",
                  }.get(d["id"], r"$^"), e["qualification"], re.I)]
    parts = []
    if bits:
        parts.append("Supported by your experience as " + "; ".join(bits[:3]))
    if quals:
        parts.append("and your " + " and ".join(quals[:2]) if parts else "Supported by your " + " and ".join(quals[:2]))
    return (" ".join(parts) + ".") if parts else "Supported by skills listed on your CV."


# ---- Outstanding information checklist ----------------------------------------------

_NUM = re.compile(r"\d")


def build_checklist(parsed: dict, rebuilt: dict) -> list[dict]:
    items: list[dict] = []

    def add(category: str, item: str, why: str, priority: str = "medium"):
        items.append({"category": category, "item": item, "why": why, "priority": priority})

    if not parsed.get("full_name"):
        add("Contact details", "Confirm your full name as it should appear at the top of the CV.",
            "The name could not be identified with confidence.", "high")
    if not parsed.get("email"):
        add("Contact details", "Add a professional email address.", "No email address was found.", "high")
    if not parsed.get("phone"):
        add("Contact details", "Add a mobile number.", "No phone number was found.", "high")
    if not parsed.get("location"):
        add("Contact details", "Add your city and province (no street address).",
            "Recruiters filter by location; a full home address is not needed.")
    if not parsed.get("linkedin_url"):
        add("Contact details", "Optional: add a LinkedIn profile URL if your profile is up to date.",
            "Many recruiters cross-check LinkedIn.", "low")

    for e in rebuilt.get("experience", []):
        label = " – ".join(x for x in [e.get("position"), e.get("employer")] if x) or "one role"
        if e.get("needs_review") or not (e.get("position") and e.get("employer")):
            add("Employment history", f"Confirm the exact job title and employer for “{label}”.",
                "The original layout made it unclear which line was the title and which the employer.", "high")
        if not e.get("start"):
            add("Employment history", f"Add start and end dates (month and year) for “{label}”.",
                "Undated roles look like gaps and are hard for an ATS to order.", "high")
        if not any(_NUM.search(b) for b in e.get("bullets", [])):
            add("Achievements", f"Add one or two verified figures for “{label}”.",
                "Examples: volumes treated or produced per shift, samples analysed per day, number of units or "
                "plants operated, audit or inspection results, people trained. Only use figures you can evidence "
                "in an interview — nothing has been estimated for you.")
        if len(e.get("bullets", [])) < 3:
            add("Employment history", f"Add more detail on your responsibilities and contributions in “{label}”.",
                "Fewer than three points makes the role look minor.", "low")

    this_year = date.today().year
    for ed in rebuilt.get("education", []) + rebuilt.get("current_studies", []):
        q = ed.get("qualification") or ed.get("institution") or "a qualification"
        st = ed.get("status")
        if st == "unverified":
            add("Qualifications", f"Confirm the status of “{q}”: completed (with year), in progress (with expected "
                                  "completion), or awaiting conferral.",
                "The CV does not make the completion status clear, so it is listed under Current Studies until "
                "confirmed.", "high")
        elif st == "awaiting_conferral":
            add("Qualifications", f"Confirm the graduation/conferral date for “{q}” once it is official.",
                "Until conferred it is shown as “Completed – awaiting conferral”, never as fully awarded.", "high")
        elif st == "in_progress":
            add("Qualifications", f"Add the expected completion date for “{q}”.",
                "Recruiters want to know when an in-progress qualification will finish.")
        elif st == "completed" and ed.get("year") and ed["year"] >= this_year - 1:
            add("Qualifications", f"Confirm that “{q}” ({ed['year']}) has been formally conferred.",
                "Recent qualifications are often still awaiting a graduation ceremony.")
        if not ed.get("institution"):
            add("Qualifications", f"Add the institution for “{q}”.", "Institution names are a common ATS filter.")
        if not ed.get("year") and st == "completed":
            add("Qualifications", f"Add the year “{q}” was completed.", "Missing years weaken credibility.")

    for c in (rebuilt.get("certifications", []) + rebuilt.get("short_courses", [])
              + rebuilt.get("in_progress_certs", [])):
        missing = [x for x, k in (("issuing body", "issuer"), ("year", "year")) if not c.get(k)]
        if missing:
            add("Certifications", f"Add the {' and '.join(missing)} for “{c.get('name')}”.",
                "Verifiable certificates carry more weight.", "low")

    if parsed.get("sensitive"):
        add("Personal details", "Removed: " + ", ".join(s["label"] for s in parsed["sensitive"])
            + ". Supply these only if an application form specifically asks.",
            "They are not needed to assess your suitability and can expose you to bias; some South African "
            "employers request ID or equity information on the application form instead of the CV.", "low")
    refs = rebuilt.get("references") or []
    if len(refs) < 2:
        add("References", f"Add {'two or three' if not refs else 'one or two more'} referees: name, job title, "
                          "organisation and phone number (or email).",
            "South African employers expect references on the CV. Ask each referee's permission first, and "
            "prefer recent supervisors over friends or family.", "high")
    for r in refs:
        if not (r.get("phone") or r.get("email")):
            add("References", f"Add a phone number or email for {r.get('name') or 'one referee'}.",
                "A referee without contact details cannot be checked.", "medium")
        if not r.get("details"):
            add("References", f"Add the job title and organisation for {r.get('name') or 'one referee'}.",
                "Recruiters want to see how the referee knows your work.", "low")
    if not parsed.get("achievements"):
        add("Achievements", "Do you have awards, recognition, improvement projects or commendations to add?",
            "None were found; a short Achievements section strengthens a technical CV.", "low")
    add("Review", "Read the new headline and professional summary and confirm every statement is accurate.",
        "They were assembled from facts in your CV, but you are the final authority on how you describe yourself.",
        "high")
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: order[x["priority"]])
    return items
