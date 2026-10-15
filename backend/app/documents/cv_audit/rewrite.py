"""Phase 2 & 4 — conservative, truth-preserving rewrite of a parsed CV.

What this module WILL do to the candidate's own words:
- remove passive openers ("Responsible for…", "Duties included…", "I was…")
  and turn a leading gerund into a verb ("Monitoring X" -> "Monitored X" for a
  past role, "Monitor X" for the current role);
- make tense consistent per role (past roles past tense, current role present);
- apply South African / British spelling ("optimize" -> "optimise");
- write a known acronym in full on its first use ("SCADA" ->
  "Supervisory Control and Data Acquisition (SCADA)");
- drop exact/near duplicate bullets, trailing full stops, and rating symbols.

What it will NEVER do: change a job title, employer, qualification name,
institution or date; upgrade a verb ("assisted" never becomes "led"); add a
number, metric, team size or outcome that is not already in the text. The
headline and summary are assembled only from facts the parser found.
"""
from __future__ import annotations

import re
from datetime import date

# ---- Verb forms -----------------------------------------------------------------

_IRREGULAR_PAST = {
    "take": "took", "lead": "led", "oversee": "oversaw", "run": "ran", "write": "wrote", "keep": "kept",
    "build": "built", "make": "made", "give": "gave", "teach": "taught", "set": "set", "draw": "drew",
    "hold": "held", "meet": "met", "find": "found", "deal": "dealt", "send": "sent", "spend": "spent",
    "understand": "understood", "undertake": "undertook", "read": "read", "feed": "fed", "do": "did",
    "get": "got", "drive": "drove", "bring": "brought", "seek": "sought", "sell": "sold", "tell": "told",
    "put": "put", "shut": "shut", "become": "became", "begin": "began", "choose": "chose",
}
_DOUBLE = {"plan", "stop", "control", "run", "set", "ship", "log", "map", "drop", "shop", "swap", "admit",
           "commit", "transfer", "refer", "patrol", "equip", "chip", "scrub", "step", "strip", "submit"}
_VERBS = """
achieve adjust administer advise align analyse analyze apply approve arrange assemble assess assist audit
balance brief build calculate calibrate check clean collaborate collect communicate compile complete conduct
configure confirm conserve consolidate construct consult contribute control convert coordinate co-ordinate
create cultivate deliver demonstrate deploy design detect determine develop diagnose direct document dose draft
drive edit educate enforce engage ensure enter establish estimate evaluate examine execute expand facilitate
file filter flush follow forecast formulate gather generate guide handle help identify implement improve
incubate induct inform initiate inspect install instruct integrate interpret investigate isolate issue label
liaise lead load log maintain manage measure mentor minimise minimize model monitor motivate negotiate observe
obtain operate optimise optimize order organise organize oversee participate perform plan prepare present
prevent prioritise process procure produce programme promote propose provide publish purchase quantify
raise read receive recommend reconcile record recruit reduce register regulate repair replace report represent
research resolve respond restore review revise run sample schedule screen secure select serve service set
sterilise sterilize stock streamline strengthen supervise supply support survey take teach test track train
transfer translate transport troubleshoot tune update upgrade use utilise validate verify weigh write
""".split()


def _past(base: str) -> str:
    if base in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[base]
    if base in _DOUBLE:
        return base + base[-1] + "ed"
    if base.endswith("e"):
        return base + "d"
    if base.endswith("y") and base[-2] not in "aeiou":
        return base[:-1] + "ied"
    return base + "ed"


def _gerund(base: str) -> str:
    if base in ("see", "flee", "agree", "free"):
        return base + "ing"
    if base.endswith("ie"):
        return base[:-2] + "ying"
    if base.endswith("e") and not base.endswith(("ee", "ye", "oe")):
        return base[:-1] + "ing"
    if base in _DOUBLE:
        return base + base[-1] + "ing"
    return base + "ing"


def _third(base: str) -> str:
    if base.endswith(("s", "sh", "ch", "x", "z", "o")):
        return base + "es"
    if base.endswith("y") and base[-2] not in "aeiou":
        return base[:-1] + "ies"
    return base + "s"


BASE_OF: dict[str, str] = {}
for _b in _VERBS:
    BASE_OF[_b] = _b
    BASE_OF[_past(_b)] = _b
    BASE_OF[_gerund(_b)] = _b
    BASE_OF[_third(_b)] = _b


# ---- Spelling & acronyms ---------------------------------------------------------

_BRITISH = {
    "optimize": "optimise", "optimized": "optimised", "optimizing": "optimising", "optimization": "optimisation",
    "organize": "organise", "organized": "organised", "organizing": "organising", "organization": "organisation",
    "organizations": "organisations", "organizational": "organisational", "analyze": "analyse",
    "analyzed": "analysed", "analyzing": "analysing", "utilize": "utilise", "utilized": "utilised",
    "utilizing": "utilising", "prioritize": "prioritise", "prioritized": "prioritised", "standardize": "standardise",
    "standardized": "standardised", "minimize": "minimise", "minimized": "minimised", "maximize": "maximise",
    "maximized": "maximised", "specialize": "specialise", "specialized": "specialised", "recognize": "recognise",
    "recognized": "recognised", "sterilize": "sterilise", "sterilized": "sterilised", "sterilization": "sterilisation",
    "neutralize": "neutralise", "neutralized": "neutralised", "stabilize": "stabilise", "stabilized": "stabilised",
    "summarize": "summarise", "summarized": "summarised", "behavior": "behaviour", "color": "colour",
    "center": "centre", "centers": "centres", "labor": "labour", "fulfill": "fulfil", "modeling": "modelling",
    "labeled": "labelled", "labeling": "labelling", "traveled": "travelled", "canceled": "cancelled",
    "license": "licence", "catalog": "catalogue", "favor": "favour", "honor": "honour", "defense": "defence",
    "liter": "litre", "liters": "litres", "meter": "metre", "meters": "metres", "fiber": "fibre",
    "sulfate": "sulphate", "sulfur": "sulphur", "aluminum": "aluminium", "program": "programme",
    "programs": "programmes", "enrollment": "enrolment", "practicing": "practising", "mold": "mould",
    "characterize": "characterise", "characterized": "characterised", "visualize": "visualise",
}
# "program" is left alone when it is clearly software ("computer program").
_SOFTWARE_CONTEXT = re.compile(r"\b(?:computer|software|python|code|coding)\s+programs?\b", re.I)

ACRONYMS: dict[str, str] = {
    "SOP": "Standard Operating Procedure", "SOPs": "Standard Operating Procedures",
    "GMP": "Good Manufacturing Practice", "GLP": "Good Laboratory Practice",
    "OHS": "Occupational Health and Safety", "OHSA": "Occupational Health and Safety Act",
    "SHEQ": "Safety, Health, Environment and Quality", "SHE": "Safety, Health and Environment",
    "HSE": "Health, Safety and Environment", "PPE": "Personal Protective Equipment",
    "SCADA": "Supervisory Control and Data Acquisition", "PLC": "Programmable Logic Controller",
    "PLCs": "Programmable Logic Controllers", "DCS": "Distributed Control System",
    "HACCP": "Hazard Analysis and Critical Control Points", "QA": "Quality Assurance", "QC": "Quality Control",
    "KPI": "Key Performance Indicator", "KPIs": "Key Performance Indicators",
    "LIMS": "Laboratory Information Management System", "WTW": "Water Treatment Works",
    "WWTW": "Wastewater Treatment Works", "NQF": "National Qualifications Framework",
    "CHIETA": "Chemical Industries Education and Training Authority",
    "EWSETA": "Energy and Water Sector Education and Training Authority",
    "ERP": "Enterprise Resource Planning", "COD": "Chemical Oxygen Demand", "BOD": "Biochemical Oxygen Demand",
    "TSS": "Total Suspended Solids", "HAZOP": "Hazard and Operability Study", "RCA": "Root Cause Analysis",
    "CAPA": "Corrective and Preventive Action", "SPC": "Statistical Process Control",
    "TPM": "Total Productive Maintenance", "OEE": "Overall Equipment Effectiveness",
    "SANS": "South African National Standards", "DWS": "Department of Water and Sanitation",
    "HIRA": "Hazard Identification and Risk Assessment", "MSDS": "Material Safety Data Sheet",
    "SDS": "Safety Data Sheet", "LOTO": "Lockout/Tagout", "QMS": "Quality Management System",
    "EMS": "Environmental Management System", "NCR": "Non-Conformance Report", "NCRs": "Non-Conformance Reports",
    "CIP": "Clean-in-Place", "HPLC": "High-Performance Liquid Chromatography",
}
_ACRONYM_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, ACRONYMS), key=len, reverse=True)) + r")\b")


def _match_case(src: str, repl: str) -> str:
    if src.isupper():
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def british(text: str) -> tuple[str, bool]:
    if not text:
        return text, False
    changed = False

    def sub(m: re.Match) -> str:
        nonlocal changed
        word = m.group(0)
        low = word.lower()
        if low in ("program", "programs") and _SOFTWARE_CONTEXT.search(text):
            return word
        repl = _BRITISH.get(low)
        if not repl:
            return word
        changed = True
        return _match_case(word, repl)

    out = re.sub(r"\b[A-Za-z]+\b", sub, text)
    return out, changed


class AcronymExpander:
    """Expands each known acronym in full the first time it appears in the
    rebuilt document (reading order), and leaves later uses short."""

    def __init__(self, full_text: str):
        self.done: set[str] = set()
        low = full_text.lower()
        for ac, full in ACRONYMS.items():
            if full.lower() in low:  # already spelt out somewhere in the CV
                self.done.add(ac.rstrip("s"))

    def __call__(self, text: str) -> tuple[str, bool]:
        changed = False

        def sub(m: re.Match) -> str:
            nonlocal changed
            ac = m.group(1)
            key = ac.rstrip("s")
            if key in self.done:
                return ac
            # Already "Full Words (ACR)" in this very string — leave it.
            before = text[max(0, m.start() - 2):m.start()]
            if before.endswith("("):
                self.done.add(key)
                return ac
            self.done.add(key)
            changed = True
            return f"{ACRONYMS[ac]} ({ac})"

        return _ACRONYM_RE.sub(sub, text), changed


# ---- Bullets -------------------------------------------------------------------

_WEAK_PREFIX = re.compile(
    r"^(?:i\s+(?:was|am)\s+|i\s+|we\s+|my\s+(?:duties|responsibilities|role)\s+(?:included|were|was|are)\s*:?\s*)?"
    r"(?:was\s+|am\s+|is\s+)?"
    r"(?:(?:responsible|accountable)\s+for|duties\s+(?:included|include|consisted\s+of)|"
    r"(?:was\s+)?tasked\s+with|key\s+duties\s*:)\s*", re.I)
_FIRST_PERSON = re.compile(r"^(?:i|we)\s+(?:(?:am|was|were|have been|had)\s+)?", re.I)
_SOFT_SWAP = {"helped with": "Assisted with", "helped": "Assisted", "help with": "Assist with"}


def polish_bullet(text: str, current: bool) -> tuple[str, list[str]]:
    changes: list[str] = []
    s = re.sub(r"\s+", " ", text).strip(" .;:-–—")
    s = re.sub(r"[★☆●○]+", "", s).strip()
    if not s:
        return s, changes

    m = _WEAK_PREFIX.match(s)
    if m and m.group(0).strip():
        rest = s[m.end():]
        first = rest.split(" ", 1)[0].lower().strip(",") if rest else ""
        if first in BASE_OF:
            s = rest
            changes.append("passive_opening")
        else:
            # "Responsible for quality checks" — keep the meaning, keep a clean opener.
            s = "Responsible for " + rest if rest else s
            if not re.match(r"^responsible for", m.group(0), re.I):
                changes.append("passive_opening")
    else:
        fp = _FIRST_PERSON.match(s)
        if fp and fp.group(0).strip():
            s = s[fp.end():]
            changes.append("first_person")

    for weak, strong in _SOFT_SWAP.items():
        if s.lower().startswith(weak + " "):
            s = strong + s[len(weak):]
            changes.append("soft_verb")
            break

    words = s.split(" ", 1)
    head = words[0].strip(",").lower()
    tail = words[1] if len(words) > 1 else ""
    base = BASE_OF.get(head)
    if base and head not in ("set", "read", "put", "shut"):
        target = base if current else _past(base)
        if target != head:
            changes.append("tense")
        s = (target + (" " + tail if tail else ""))
    elif base:
        s = head + (" " + tail if tail else "")

    s, brit = british(s)
    if brit:
        changes.append("spelling")
    s = s[0].upper() + s[1:] if s else s
    return s.rstrip(" .;"), changes


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def dedupe(items: list[str]) -> list[str]:
    out, seen = [], set()
    for it in items:
        k = _norm_key(it)
        if not k or k in seen:
            continue
        if any(k in o or o in k for o in seen if len(o) > 25 and len(k) > 25):
            continue
        seen.add(k)
        out.append(it)
    return out


# ---- Competency taxonomy (evidence-based) -----------------------------------------

COMPETENCY_GROUPS: list[tuple[str, list[str]]] = [
    ("Water and Wastewater Treatment", [
        "water treatment", "wastewater", "waste water", "sedimentation", "filtration", "filters", "clarifier",
        "coagulation", "flocculation", "disinfection", "chlorination", "jar test", "turbidity", "potable water",
        "raw water", "sludge", "effluent", "reservoir", "water quality", "water purification", "abstraction",
        "dosing", "water sampling", "water samples", "bulk water", "filter"]),
    ("Process Operations and Control", [
        "process control", "process monitoring", "process controller", "scada", "plc", "dcs", "plant operation",
        "control room", "shift operation", "process optimisation", "process optimization", "troubleshoot",
        "start-up", "shutdown", "production", "process data", "plant", "operations", "mass balance", "process"]),
    ("Laboratory and Microbiology", [
        "microbiolog", "culture media", "aseptic", "laboratory", "lab ", "titration", "spectrophotomet",
        "chromatograph", "hplc", "lims", "calibrat", "sample analysis", "sampling", "analysis", "biotechnolog",
        "incubat", "assay", "ph "]),
    ("Quality Assurance and Compliance", [
        "quality control", "quality assurance", "quality", "gmp", "glp", "iso 9001", "iso", "haccp", "audit",
        "non-conformance", "capa", "root cause", "spc", "compliance", "sop", "standard operating procedure",
        "regulatory", "specification"]),
    ("Occupational Health and Safety", [
        "ohs", "occupational health", "safety", "risk assessment", "incident", "ppe", "permit to work", "hazop",
        "sheq", "first aid", "lockout", "hazard", "emergency", "inspection"]),
    ("Maintenance Coordination and Equipment Reliability", [
        "maintenance", "equipment fault", "preventive maintenance", "preventative maintenance", "breakdown",
        "equipment", "reliability", "artisan", "repairs"]),
    ("Operations Management and Continuous Improvement", [
        "operations management", "supply chain", "scheduling", "production planning", "kpi", "budget", "lean",
        "six sigma", "continuous improvement", "project management", "inventory", "logistics",
        "performance monitoring", "efficiency", "cost"]),
    ("Data Recording, Reporting and Documentation", [
        "data recording", "record", "logbook", "log book", "reporting", "report", "documentation",
        "technical report", "spreadsheet", "data capture", "data analysis"]),
    ("Teamwork, Communication and Leadership", [
        "teamwork", "team player", "communication", "training", "mentor", "leadership", "supervis",
        "problem solving", "problem-solving", "coaching", "interpersonal", "liaise", "stakeholder"]),
]
SOFTWARE_TERMS = ["microsoft excel", "excel", "microsoft word", "ms word", "word", "powerpoint", "ms office",
                  "microsoft office", "outlook", "sap", "scada", "lims", "autocad", "power bi", "python", "matlab",
                  "minitab", "qgis", "arcgis", "sql", "wonderware", "citect", "syspro", "pastel", "sage", "teams",
                  "google workspace", "r ", "spss", "tableau", "erp"]

# Phrases worth surfacing as competencies when the candidate's OWN bullets use them.
EVIDENCE_PHRASES: list[tuple[str, str]] = [
    ("chemical dosing", "Chemical dosing"), ("jar test", "Jar testing"), ("turbidity", "Turbidity monitoring"),
    ("sedimentation", "Sedimentation process monitoring"), ("filtration", "Filtration"),
    ("filters", "Filter operation"), ("disinfection", "Disinfection"), ("chlorination", "Chlorination"),
    ("water samples", "Water sampling"), ("sampling", "Sampling"), ("scada", "SCADA"),
    ("process data", "Process data recording"), ("logbook", "Process logbooks"),
    ("incident", "Incident reporting"), ("equipment fault", "Equipment fault reporting"),
    ("quality control", "Quality control"), ("quality assurance", "Quality assurance"),
    ("glp", "GLP"), ("gmp", "GMP"), ("sop", "SOPs"), ("safety", "Workplace safety"),
    ("ohs", "OHS"), ("microbiological testing", "Microbiological testing"), ("culture media", "Culture media preparation"),
    ("laboratory equipment", "Laboratory equipment maintenance"), ("calibrat", "Instrument calibration"),
    ("training", "On-the-job training"), ("inspection", "Inspections"), ("audit", "Audits"),
    ("root cause", "Root cause analysis"), ("continuous improvement", "Continuous improvement"),
    ("risk assessment", "Risk assessment"), ("ph ", "pH analysis"), ("ph analysis", "pH analysis"),
    ("maintenance", "Maintenance coordination"), ("production", "Production operations"),
]


def group_for(term: str) -> str | None:
    low = f" {term.lower()} "
    for label, keys in COMPETENCY_GROUPS:
        if any(k in low for k in keys):
            return label
    return None


def is_software(term: str) -> bool:
    low = f" {term.lower()} "
    return any(f" {t.strip()} " in low or low.strip() == t.strip() for t in SOFTWARE_TERMS)


def build_competencies(skills: list[str], bullets: list[str], education: list[dict]) -> tuple[dict, list[str]]:
    """Returns ({group_label: [terms]}, software). Every term is the candidate's
    own listed skill or a phrase that literally appears in their own bullets."""
    groups: dict[str, list[str]] = {}
    software: list[str] = []
    seen: set[str] = set()

    def add(term: str):
        t = term.strip(" .")
        k = t.lower()
        if not t or k in seen:
            return
        seen.add(k)
        if is_software(t) and len(t.split()) <= 3 and t.upper() != "SCADA":
            software.append(t)
            return
        g = group_for(t) or "Additional Skills"
        groups.setdefault(g, []).append(t)

    for s in skills:
        add(s)
    blob = " " + " ".join(bullets).lower() + " "
    for needle, label in EVIDENCE_PHRASES:
        if needle in blob:
            # Skip if an existing term already covers it.
            if any(label.lower() in x or x in label.lower() for x in seen):
                continue
            add(label)
    ordered = {}
    for label, _ in COMPETENCY_GROUPS:
        if label in groups:
            ordered[label] = groups[label][:8]
    if "Additional Skills" in groups:
        ordered["Additional Skills"] = groups["Additional Skills"][:8]
    return ordered, software


def domain_evidence(cv: dict) -> list[tuple[str, int]]:
    """Rank competency groups by how much of the CV's own text supports them.
    The current (or most recent) role counts triple — it is what the candidate
    does now, so it should lead the headline and summary."""
    weighted: list[tuple[str, int]] = [(cv.get("summary") or "", 1), (" ".join(cv.get("skills", [])), 1)]
    exp = cv.get("experience", []) or []
    for i, e in enumerate(exp):
        w = 3 if (e.get("is_current") or i == 0) else 1
        weighted.append((" ".join([e.get("position") or "", e.get("employer") or "",
                                   " ".join(e.get("bullets", []))]), w))
    for ed in cv.get("education", []):
        weighted.append((ed.get("qualification") or "", 1))
    for c in cv.get("certifications", []):
        weighted.append((c.get("name") or "", 1))
    scores = []
    for label, keys in COMPETENCY_GROUPS:
        n = 0
        for text, w in weighted:
            blob = " " + text.lower() + " "
            n += w * sum(blob.count(k) for k in keys)
        if n:
            scores.append((label, n))
    scores.sort(key=lambda x: -x[1])
    return scores


_HEADLINE_SHORT = {
    "Water and Wastewater Treatment": "Water & Wastewater Treatment",
    "Process Operations and Control": "Process Operations & Control",
    "Laboratory and Microbiology": "Laboratory & Microbiology",
    "Quality Assurance and Compliance": "Quality Assurance & Compliance",
    "Occupational Health and Safety": "Occupational Health & Safety",
    "Maintenance Coordination and Equipment Reliability": "Maintenance & Reliability",
    "Operations Management and Continuous Improvement": "Operations Management",
    "Data Recording, Reporting and Documentation": "Technical Reporting",
    "Teamwork, Communication and Leadership": "Team Leadership",
}

_SUMMARY_SHORT = {
    "Water and Wastewater Treatment": "water treatment",
    "Process Operations and Control": "process operations",
    "Laboratory and Microbiology": "laboratory and microbiology",
    "Quality Assurance and Compliance": "quality assurance",
    "Occupational Health and Safety": "occupational health and safety",
    "Maintenance Coordination and Equipment Reliability": "maintenance coordination",
    "Operations Management and Continuous Improvement": "operations management",
}

_QUAL_RANK = [
    (r"doctor|phd|ph\.d", 8), (r"master|mba|m\.?sc|m\.?tech", 7), (r"postgraduate|pgdip|honours|hons", 6),
    (r"advanced diploma|b\.?tech|bachelor|degree|b\.?sc|b\.?com", 5), (r"diploma", 4),
    (r"higher certificate|advanced certificate|national certificate|occupational certificate", 3),
    (r"certificate|n[4-6]\b", 2), (r"matric|grade 12|senior certificate", 1),
]


def qual_rank(q: str | None) -> int:
    low = (q or "").lower()
    for pat, r in _QUAL_RANK:
        if re.search(pat, low):
            return r
    return 0


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in "aeiou" else "a"


def build_headline(cv: dict) -> tuple[str, str]:
    """(headline, basis). Title comes from the most recent role exactly as written."""
    exp = cv.get("experience") or []
    title = None
    if exp:
        cur = next((e for e in exp if e.get("is_current")), exp[0])
        title = cur.get("position")
    src = (cv.get("headline") or "").strip()
    if not title and src:
        title = re.split(r"\s*[|•·,]\s*", src)[0]
    domains = [d for d, _ in domain_evidence(cv) if d not in ("Teamwork, Communication and Leadership",
                                                               "Data Recording, Reporting and Documentation")]
    parts = [title] if title else []
    for d in domains:
        if len(parts) >= (3 if title else 2):
            break
        short = _HEADLINE_SHORT.get(d, d)
        if title and short.split()[0].lower() in title.lower():
            continue  # "Process Controller | Process Operations…" says the same thing twice
        parts.append(short)
    parts = parts[:3]
    if not parts:
        return src or "", "kept from your CV"
    return " | ".join(parts), "most recent job title plus the two areas your CV evidences most"


_EXPLICIT_YEARS = re.compile(r"(\d{1,2})\+?\s*years?\s*(?:of\s*)?(?:relevant\s*|professional\s*|working\s*|work\s*|industry\s*)?experience", re.I)


def build_summary(cv: dict, source_text: str) -> str:
    exp = cv.get("experience") or []
    edu = cv.get("education") or []
    sentences: list[str] = []

    title = None
    current = next((e for e in exp if e.get("is_current")), None)
    if exp:
        title = (current or exp[0]).get("position")
    domains = [d for d, _ in domain_evidence(cv)
               if d not in ("Teamwork, Communication and Leadership", "Data Recording, Reporting and Documentation")]
    domain_txt = _join([_SUMMARY_SHORT.get(d, d.lower()) for d in domains[:3]])
    m = _EXPLICIT_YEARS.search(source_text or "")
    years_txt = f" with {m.group(1)} years of experience" if m else ""
    earliest = None
    for e in exp:
        y = re.search(r"(19|20)\d{2}", e.get("start") or "")
        if y:
            earliest = min(earliest or 9999, int(y.group(0)))
    if not years_txt and earliest and earliest < date.today().year:
        years_txt = f" with professional experience since {earliest}"
    if title:
        s = f"{title}{years_txt}"
        if domain_txt:
            s += f" across {domain_txt}"
        employers = []
        for e in exp:
            if e.get("employer") and e["employer"] not in employers:
                employers.append(e["employer"])
        if current and current.get("employer"):
            s += f", currently with {current['employer']}"
            others = [x for x in employers if x != current["employer"]][:2]
            if others:
                s += f" and previously with {_join(others)}"
        elif employers:
            s += f", with experience at {_join(employers[:3])}"
        sentences.append(s + ".")

    done = sorted([e for e in edu if e.get("status") == "completed" and qual_rank(e.get("qualification")) >= 2],
                  key=lambda e: -qual_rank(e.get("qualification")))
    pending = [e for e in edu if e.get("status") in ("in_progress", "awaiting_conferral")]
    if done:
        quals = [d["qualification"] for d in done[:2]]
        s = "Holds " + _join([f"{_article(q)} {q}" for q in quals])
        if pending:
            p = pending[0]
            verb = "awaiting conferral of" if p["status"] == "awaiting_conferral" else "currently completing"
            s += f", and is {verb} {_article(p['qualification'] or 'a')} {p['qualification']}"
        sentences.append(s + ".")
    elif pending:
        p = pending[0]
        verb = "Awaiting conferral of" if p["status"] == "awaiting_conferral" else "Currently completing"
        sentences.append(f"{verb} {_article(p['qualification'] or 'a')} {p['qualification']}.")

    comp, _ = build_competencies(cv.get("skills", []), [b for e in exp for b in e.get("bullets", [])], edu)
    tech = [t for g, ts in comp.items() if g not in ("Teamwork, Communication and Leadership", "Additional Skills")
            for t in ts]
    if tech:
        sentences.append(f"Technical strengths include {_join([t[0].lower() + t[1:] if not t[:2].isupper() else t for t in tech[:5]])}.")

    blob = " ".join([" ".join(e.get("bullets", [])) for e in exp]).lower()
    strengths = []
    if re.search(r"incident", blob):
        strengths.append("workplace safety and incident reporting")
    elif re.search(r"safety|ohs|ppe|hazard", blob):
        strengths.append("workplace safety")
    if re.search(r"\bsop|standard operating|gmp|glp|complian", blob):
        strengths.append("procedural compliance")
    if re.search(r"quality|qc\b|qa\b", blob):
        strengths.append("quality control")
    if re.search(r"record|logbook|report|data", blob):
        strengths.append("accurate process records")
    if strengths:
        sentences.append(f"Day-to-day work spans {_join(strengths[:4])}.")
    out = " ".join(sentences)
    out, _ = british(out)
    return out


def build_rebuilt_cv(parsed: dict, source_text: str) -> tuple[dict, list[dict]]:
    """Rebuild the CV (dict for render.py) plus a change log for the report."""
    log: list[dict] = []
    full_text = " ".join([
        parsed.get("summary") or "", " ".join(parsed.get("skills", [])),
        " ".join(b for e in parsed.get("experience", []) for b in e.get("bullets", [])),
    ])
    expand = AcronymExpander(full_text)

    headline, basis = build_headline(parsed)
    if headline and headline != (parsed.get("headline") or ""):
        log.append({"area": "Headline", "change": f"Headline set to “{headline}” ({basis})."})
    summary = build_summary(parsed, source_text)
    if summary:
        log.append({"area": "Summary", "change": "Professional summary rewritten from facts in your CV "
                                                 "(roles, employers, qualifications, evidenced skills)."})
        summary, _ = expand(summary)

    experience = []
    change_counts: dict[str, int] = {}
    for e in parsed.get("experience", []):
        current = bool(e.get("is_current"))
        bullets = []
        for b in e.get("bullets", []):
            nb, ch = polish_bullet(b, current)
            for c in ch:
                change_counts[c] = change_counts.get(c, 0) + 1
            if nb:
                bullets.append(nb)
        experience.append({**e, "bullets": dedupe(bullets)})

    # Competencies are built from the polished (not yet expanded) wording, then
    # acronyms are expanded in READING order: summary, competencies, experience.
    comp, software = build_competencies(parsed.get("skills", []),
                                        [b for e in experience for b in e["bullets"]], parsed.get("education", []))
    comp = {g: [expand(t)[0] if t.rstrip("s").isupper() else t for t in ts] for g, ts in comp.items()}
    software = dedupe(software + [s for s in parsed.get("software", []) if s not in software])
    for e in experience:
        out = []
        for b in e["bullets"]:
            nb, ch = expand(b)
            if ch:
                change_counts["acronym"] = change_counts.get("acronym", 0) + 1
            out.append(nb)
        e["bullets"] = out

    labels = {"passive_opening": "passive openings such as “responsible for” removed",
              "first_person": "first-person “I” removed", "tense": "verb tense made consistent",
              "spelling": "South African/British spelling applied", "acronym": "acronyms written in full on first use",
              "soft_verb": "informal verbs replaced with equivalent professional wording"}
    for k, n in change_counts.items():
        log.append({"area": "Experience", "change": f"{n} × {labels.get(k, k)}."})
    if parsed.get("sensitive"):
        log.append({"area": "Personal details", "change": "Removed: " + ", ".join(s["label"] for s in parsed["sensitive"])
                    + ". Not required on a professional CV and a POPIA/discrimination risk."})
    if parsed.get("references_present"):
        log.append({"area": "References", "change": "Referee names and numbers removed — provide them when requested."})

    edu = parsed.get("education", [])
    completed = [e for e in edu if e.get("status") == "completed"]
    current_studies = [e for e in edu if e.get("status") in ("in_progress", "awaiting_conferral", "unverified")]
    completed.sort(key=lambda e: (-(e.get("year") or 0), -qual_rank(e.get("qualification"))))

    certs = parsed.get("certifications", [])
    cv = {
        "full_name": parsed.get("full_name"),
        "headline": headline,
        "email": parsed.get("email"), "phone": parsed.get("phone"), "location": parsed.get("location"),
        "linkedin_url": parsed.get("linkedin_url"), "links": parsed.get("links", []),
        "summary": summary,
        "competencies": comp,
        "software": software,
        "experience": experience,
        "education": completed,
        "current_studies": current_studies,
        "certifications": [c for c in certs if c.get("kind") in ("certification",) and c.get("status") == "completed"],
        "short_courses": [c for c in certs if c.get("kind") == "short_course" and c.get("status") == "completed"],
        "in_progress_certs": [c for c in certs if c.get("status") == "in_progress"],
        "registrations": [c for c in certs if c.get("kind") in ("registration", "membership")]
                         + [{"name": m, "issuer": None, "year": None, "kind": "membership", "status": "completed"}
                            for m in parsed.get("memberships", [])],
        "projects": [polish_bullet(p, False)[0] for p in parsed.get("projects", [])][:6],
        "achievements": [polish_bullet(a, False)[0] for a in parsed.get("achievements", [])][:6],
        "languages": parsed.get("languages", []),
        "drivers_licence": parsed.get("drivers_licence"),
    }
    return cv, log
