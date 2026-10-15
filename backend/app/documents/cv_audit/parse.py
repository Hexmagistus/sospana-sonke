"""Phase 1b — deterministic section parser for an uploaded CV's extracted text.

Richer than app/ai/heuristic.py (which only feeds the profile importer): this
one keeps experience entries together with their dates and bullet points,
records each qualification's completion status, separates certifications from
memberships and short courses, and notes sensitive personal data so the
rebuild can leave it out.

It is conservative by design. When it cannot tell which half of a line is the
job title and which the employer, it says so (``needs_review``) rather than
pretending; the candidate can fix it on the review screen before downloading.
Nothing here invents a value — every field is a substring of the source text
(lightly normalised: whitespace, bullet glyphs, date formats).
"""
from __future__ import annotations

import re
from datetime import date

# ---- Headings ---------------------------------------------------------------

HEADINGS: dict[str, list[str]] = {
    "summary": ["professional summary", "summary", "profile", "professional profile", "career profile",
                "personal profile", "career summary", "career objective", "objective", "objectives",
                "about me", "executive summary", "personal statement", "career overview", "overview"],
    "skills": ["skills", "key skills", "core skills", "core competencies", "competencies", "technical skills",
               "skills and competencies", "skills & competencies", "key competencies", "areas of expertise",
               "expertise", "strengths", "key strengths", "skills summary", "abilities", "technical competencies",
               "professional skills", "soft skills", "skills and abilities", "core competencies and skills"],
    "software": ["computer skills", "computer literacy", "software", "it skills", "software skills",
                 "digital skills", "technical tools", "tools", "systems", "software and systems"],
    "experience": ["work experience", "experience", "professional experience", "employment history",
                   "employment", "career history", "work history", "employment record", "relevant experience",
                   "professional background", "career experience", "working experience", "employment experience",
                   "experience and employment", "career progression", "professional history"],
    "education": ["education", "qualifications", "academic qualifications", "education and training",
                  "educational background", "academic background", "tertiary education", "academic history",
                  "education & qualifications", "education and qualifications", "academic record",
                  "formal education", "academic achievements", "qualification"],
    "certifications": ["certifications", "certificates", "certification", "courses", "short courses",
                       "training", "professional development", "licences", "licenses", "training and development",
                       "additional training", "professional training", "courses and certifications",
                       "certifications and training", "training courses", "accreditations",
                       "licenses and certifications", "licences and certifications", "workshops"],
    "memberships": ["professional memberships", "memberships", "affiliations", "professional affiliations",
                    "professional bodies", "professional registrations", "registrations"],
    "projects": ["projects", "selected projects", "key projects", "research", "research projects",
                 "publications", "research and publications"],
    "achievements": ["achievements", "key achievements", "awards", "awards and achievements", "honours and awards",
                     "awards and recognition", "accomplishments", "recognition"],
    "languages": ["languages", "language proficiency", "language skills", "languages spoken"],
    "personal": ["personal details", "personal information", "personal particulars", "personal data",
                 "biographical details", "personal info"],
    "references": ["references", "referees", "reference", "professional references"],
    "interests": ["interests", "hobbies", "hobbies and interests", "interests and hobbies", "extracurricular activities",
                  "extra-curricular activities", "community involvement", "volunteering", "volunteer work",
                  "leadership and community", "volunteer experience"],
    "contact": ["contact", "contact details", "contact information"],
    "declaration": ["declaration", "declarations"],
    "_title": ["curriculum vitae", "resume", "résumé", "cv"],
}
_HEADING_LOOKUP = {syn: canon for canon, syns in HEADINGS.items() for syn in syns}
STANDARD_HEADINGS = {"summary", "skills", "software", "experience", "education", "certifications",
                     "memberships", "projects", "achievements", "languages", "interests"}


def _norm_heading(line: str) -> str:
    s = re.sub(r"[^\w&' ]+", " ", line.lower()).strip()
    return re.sub(r"\s+", " ", s)


def heading_of(line: str) -> str | None:
    """Return the canonical section for a heading line, or None."""
    raw = line.strip()
    if not raw or len(raw) > 60:
        return None
    norm = _norm_heading(raw)
    if norm in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[norm]
    words = norm.split()
    if raw.endswith(":") and 1 <= len(words) <= 4:
        # An explicit "Something:" label line we do not recognise.
        return "_other"
    return None


# ---- Dates ------------------------------------------------------------------

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MON = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_YEAR = r"(?:19[5-9]\d|20[0-4]\d)"
_DATE = rf"(?:{_MON}\.?\s*,?\s*{_YEAR}|\d{{1,2}}\s*[/.-]\s*{_YEAR}|{_YEAR}\s*[/.-]\s*\d{{1,2}}(?!\d)|{_YEAR})"
_OPEN = r"(?:present|current|currently|date|to date|now|ongoing|till date|todate)"
DATE_RANGE = re.compile(rf"({_DATE})\s*(?:-|–|—|to|until|till|→)\s*({_DATE}|{_OPEN})", re.I)
SINGLE_DATE = re.compile(rf"\b({_DATE})\b", re.I)


def norm_date(token: str) -> str:
    """'january 2020' -> 'Jan 2020', '03/2021' -> 'Mar 2021', '2019' -> '2019'."""
    t = token.strip().lower().replace(",", " ")
    if re.fullmatch(_OPEN, t, re.I):
        return "Present"
    m = re.match(rf"({_MON})\.?\s*({_YEAR})", t, re.I)
    if m:
        return f"{_MONTH_NAMES[_MONTHS[m.group(1)[:3]] - 1]} {m.group(2)}"
    m = re.match(rf"(\d{{1,2}})\s*[/.-]\s*({_YEAR})", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{_MONTH_NAMES[int(m.group(1)) - 1]} {m.group(2)}"
    m = re.match(rf"({_YEAR})\s*[/.-]\s*(\d{{1,2}})", t)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{_MONTH_NAMES[int(m.group(2)) - 1]} {m.group(1)}"
    m = re.search(_YEAR, t)
    return m.group(0) if m else token.strip()


def year_of(value: str | None) -> int | None:
    if not value:
        return None
    m = re.search(_YEAR, value)
    return int(m.group(0)) if m else None


# ---- Contact & sensitive data --------------------------------------------------

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s.-]?\(?0?\)?[\s.-]?\d{2,3}|\(?0\d{2}\)?)[\s.-]?\d{3}[\s.-]?\d{3,4}(?!\d)")
LINKEDIN = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/[^\s,|)]+", re.I)
URL = re.compile(r"(?:https?://|www\.)[^\s,|)]+", re.I)
SA_ID = re.compile(r"(?<!\d)\d{6}\s?\d{4}\s?\d{2}\s?\d(?!\d)")

_SENSITIVE_LABELS = {
    "id_number": r"(?:id|identity)\s*(?:no|number|#)?|passport\s*(?:no|number)?",
    "date_of_birth": r"date\s*of\s*birth|d\.?o\.?b\.?|birth\s*date|born",
    "age": r"age",
    "gender": r"gender|sex",
    "marital_status": r"marital\s*status|married|single",
    "nationality": r"nationality|citizenship",
    "religion": r"religion|church|denomination",
    "race": r"race|ethnicity|ethnic\s*group|population\s*group|equity\s*status|ee\s*status",
    "health": r"health(?:\s*status)?|disability|disabilities|medical",
    "dependants": r"dependants|dependents|children",
    "criminal_record": r"criminal\s*record|criminal\s*offences?",
    "home_address": r"(?:home|residential|physical|postal)?\s*address",
    "salary": r"(?:current|expected)\s*salary|salary\s*expectations?|remuneration",
    "reason_for_leaving": r"reason\s*for\s*leaving",
}
_SENSITIVE_RE = {k: re.compile(rf"^\s*(?:{v})\s*[:\-–]\s*(.+)$", re.I) for k, v in _SENSITIVE_LABELS.items()}
SENSITIVE_LABEL_TEXT = {
    "id_number": "ID or passport number", "date_of_birth": "Date of birth", "age": "Age",
    "gender": "Gender", "marital_status": "Marital status", "nationality": "Nationality / citizenship",
    "religion": "Religion", "race": "Race / equity status", "health": "Health or disability status",
    "dependants": "Dependants", "criminal_record": "Criminal record statement",
    "home_address": "Full home address", "salary": "Salary details", "reason_for_leaving": "Reasons for leaving",
}

_DRIVERS = re.compile(r"^\s*(?:driver'?s?|drivers)\s*(?:licen[cs]e|license)\s*(?:code)?\s*[:\-–]?\s*(.*)$", re.I)
_LANG_LABEL = re.compile(r"^\s*(?:languages?|home\s*language|other\s*languages?)\s*[:\-–]\s*(.+)$", re.I)
_NAME_LABEL = re.compile(r"^\s*(?:full\s*names?|name|names|first\s*names?)\s*[:\-–]\s*(.+)$", re.I)
_SURNAME_LABEL = re.compile(r"^\s*surname\s*[:\-–]\s*(.+)$", re.I)
_LOCATION_LABEL = re.compile(r"^\s*(?:location|city|town|based\s*in|residence|area)\s*[:\-–]\s*(.+)$", re.I)
_EMAIL_LABEL = re.compile(r"^\s*(?:e-?mail(?:\s*address)?)\s*[:\-–]\s*", re.I)
_PHONE_LABEL = re.compile(r"^\s*(?:cell(?:phone)?|mobile|phone|tel(?:ephone)?|contact\s*(?:no|number)?)\s*(?:no\.?|number)?\s*[:\-–]\s*", re.I)

# ---- Vocabulary for classifying header pieces ---------------------------------

ROLE_WORDS = {
    "controller", "technician", "technologist", "operator", "manager", "assistant", "supervisor", "engineer",
    "analyst", "officer", "intern", "internship", "learner", "learnership", "specialist", "coordinator",
    "co-ordinator", "clerk", "scientist", "chemist", "consultant", "director", "lead", "head", "administrator",
    "artisan", "attendant", "developer", "producer", "founder", "co-founder", "owner", "chief", "executive",
    "representative", "agent", "trainee", "graduate", "apprentice", "foreman", "planner", "inspector",
    "auditor", "accountant", "lecturer", "tutor", "teacher", "educator", "researcher", "microbiologist",
    "biotechnologist", "fitter", "electrician", "mechanic", "driver", "cashier", "receptionist", "secretary",
    "programmer", "designer", "architect", "nurse", "doctor", "pharmacist", "advisor", "adviser", "associate",
    "practitioner", "monitor", "handler", "worker", "superintendent", "leader", "ambassador", "volunteer",
    "facilitator", "assessor", "moderator", "buyer", "storeman", "controller's", "president", "secretary-general",
}
ORG_WORDS = {
    "pty", "(pty)", "ltd", "limited", "inc", "group", "holdings", "corporation", "company", "co.", "cc",
    "municipality", "municipal", "department", "university", "college", "institute", "board", "authority",
    "agency", "council", "trust", "foundation", "bank", "hospital", "clinic", "plant", "works", "mine", "mines",
    "refinery", "laboratories", "laboratory", "industries", "industrial", "services", "solutions", "consulting",
    "technologies", "systems", "sa", "rsa", "africa", "african", "international", "enterprises", "partners",
    "associates", "water", "eskom", "sasol", "transnet", "starch", "foods", "beverages", "chemicals",
    "creative", "studio", "studios", "school", "academy", "ministry", "government", "metro", "city", "ngo",
    "npc", "npo", "(npc)", "soc", "(soc)", "facility",
}
SA_PLACES = {
    "johannesburg", "pretoria", "tshwane", "cape town", "durban", "ethekwini", "vereeniging", "vanderbijlpark",
    "sasolburg", "meyerton", "sebokeng", "soweto", "polokwane", "mbombela", "nelspruit", "bloemfontein",
    "kimberley", "rustenburg", "mahikeng", "east london", "gqeberha", "port elizabeth", "pietermaritzburg",
    "secunda", "witbank", "emalahleni", "middelburg", "germiston", "benoni", "boksburg", "springs", "kempton park",
    "midrand", "centurion", "sandton", "randburg", "roodepoort", "krugersdorp", "potchefstroom", "klerksdorp",
    "welkom", "george", "stellenbosch", "richards bay", "newcastle", "ladysmith", "bellville", "gauteng",
    "western cape", "eastern cape", "kwazulu-natal", "kwazulu natal", "limpopo", "mpumalanga", "north west",
    "free state", "northern cape", "south africa", "vaal triangle", "vaal", "bronkhorstspruit", "evaton",
    "orange farm", "lenasia", "alberton", "edenvale", "bedfordview", "heidelberg", "nigel", "zuikerbosch",
}
QUAL_WORDS = re.compile(
    r"\b(?:diploma|degree|bachelor|b\.?\s?sc|bsc|b\.?\s?com|bcom|b\.?\s?tech|btech|b\.?\s?eng|beng|b\.?a\b|"
    r"honours|hons|master'?s?|m\.?\s?sc|msc|mba|m\.?\s?tech|mtech|phd|ph\.d|doctorate|doctor of|"
    r"national certificate|higher certificate|advanced certificate|certificate|nqf|matric|grade 12|"
    r"senior certificate|n[1-6]\b|postgraduate|post-graduate|pgdip|nated|national senior certificate|"
    r"qualification|learnership|occupational certificate|further education)\b", re.I)
INSTITUTION_WORDS = re.compile(
    r"\b(?:university|universiteit|college|institute|institution|school|academy|tvet|technikon|unisa|"
    r"polytechnic|seta|chieta|merseta|ewseta|lgseta|varsity|campus|vut|tut|uj|wits|ukzn|nwu|cput|dut|mut|cut)\b", re.I)

IN_PROGRESS = re.compile(
    r"\b(?:in progress|currently (?:studying|enrolled|completing|pursuing|registered)|currently|ongoing|"
    r"pursuing|studying|enrolled|expected(?: completion)?|anticipated|to be completed|underway|final year|"
    r"(?:1st|2nd|3rd|first|second|third) year|incomplete|not yet completed|present|current)\b", re.I)
AWAITING = re.compile(
    r"\b(?:awaiting (?:graduation|conferral|certificate|results|confirmation)|pending (?:graduation|conferral|results)|"
    r"to be conferred|graduation pending|completed,? awaiting|awaiting)\b", re.I)
COMPLETED = re.compile(r"\b(?:completed|obtained|graduated|conferred|awarded|passed|achieved|cum laude)\b", re.I)

_GLYPHS = "•·▪▫■□◦●○◆◇➢➤►▶✓✔✦✧❖\x7f\uf0b7\uf0a7\uf076\uf0d8\uf0fc\uf0a8\u2023\u2043"
BULLET_RE = re.compile(r"^\s*(?:[•·▪▫■□◦●○◆◇➢➤►▶✓✔✦✧❖\x7f\uf0b7\uf0a7\uf076\uf0d8\uf0fc\uf0a8\u2023\u2043\-–—*>]|\d{1,2}[.)]|[a-z][.)]|o\s)\s*")


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", line.replace(" ", " ")).strip(" \t|")


def _is_bullet(raw: str) -> bool:
    return bool(BULLET_RE.match(raw)) and not re.match(r"^\s*\d{1,2}[.)]\s*\d", raw)


def _strip_bullet(raw: str) -> str:
    return _clean(BULLET_RE.sub("", raw, count=1))


def _split_pieces(text: str) -> list[str]:
    parts = re.split(r"\s*(?:\||•|·|\s[–—-]\s|,\s(?=[A-Z])|\sat\s(?=[A-Z]))\s*", text)
    return [p.strip(" ,;:-–—()") for p in parts if p and p.strip(" ,;:-–—()")]


def _looks_role(piece: str) -> bool:
    words = {w.strip("(),.").lower() for w in piece.split()}
    return bool(words & ROLE_WORDS)


def _looks_org(piece: str) -> bool:
    low = piece.lower()
    words = {w.strip(",.").lower() for w in piece.split()}
    return bool(words & ORG_WORDS) or bool(re.search(r"\(pty\)|\bltd\b|\bsoc\b", low))


def _looks_place(piece: str) -> bool:
    low = piece.lower().strip()
    if low in SA_PLACES:
        return True
    parts = [p.strip() for p in low.split(",")]
    return all(p in SA_PLACES for p in parts if p) and bool(parts)


def _looks_like_name(line: str) -> bool:
    if EMAIL.search(line) or any(ch.isdigit() for ch in line) or len(line) > 45:
        return False
    words = line.replace(",", " ").split()
    if not 2 <= len(words) <= 5:
        return False
    if heading_of(line):
        return False
    if _looks_org(line) or _looks_role(line):
        return False
    return all(w[0].isupper() or w.isupper() for w in words if w[0].isalpha())


def _title_case_name(name: str) -> str:
    if name.isupper():
        return " ".join(w.capitalize() if len(w) > 2 else w for w in name.split())
    return name


# ---- Parsing --------------------------------------------------------------------

def normalise_lines(lines: list[str]) -> list[str]:
    """Repair the two commonest PDF-extraction artefacts: a bullet glyph on a
    line of its own (the text follows on the next line), and a long bullet
    wrapped onto a continuation line that starts in lower case."""
    out: list[str] = []
    pending_bullet = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if all(ch in _GLYPHS or ch.isspace() for ch in stripped):
            pending_bullet = True
            continue
        if pending_bullet:
            out.append("• " + stripped)
            pending_bullet = False
            continue
        if out and _is_bullet(out[-1]) and stripped[:1].islower() and not BULLET_RE.match(raw):
            out[-1] = out[-1].rstrip() + " " + stripped
            continue
        out.append(raw)
    return out


def _sections(lines: list[str]) -> tuple[list[tuple[str, list[str]]], list[dict]]:
    """Split raw lines into (canonical_section, lines). '_header' is the block
    before the first heading. Also returns the headings exactly as written."""
    out: list[tuple[str, list[str]]] = [("_header", [])]
    headings: list[dict] = []
    for raw in lines:
        clean = _clean(raw)
        if not clean:
            continue
        canon = heading_of(clean)
        if canon == "_title":
            continue
        if canon:
            headings.append({"text": clean.rstrip(":"), "canonical": canon})
            out.append((canon, []))
            continue
        # "Skills: Excel, SAP" — a heading with inline content.
        m = re.match(r"^([A-Za-z &/'-]{3,40})\s*:\s*(.+)$", clean)
        if m and m.group(1).strip().lower() in _HEADING_LOOKUP and \
                _HEADING_LOOKUP[m.group(1).strip().lower()] not in ("_title", "contact", "personal"):
            canon = _HEADING_LOOKUP[m.group(1).strip().lower()]
            headings.append({"text": m.group(1).strip(), "canonical": canon})
            out.append((canon, [m.group(2)]))
            continue
        out[-1][1].append(raw)
    return out, headings


def _parse_experience(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    cur: dict | None = None

    def new() -> dict:
        return {"headers": [], "start": None, "end": None, "is_current": False, "date_text": None,
                "bullets": [], "location": None, "labelled": {}}

    def flush():
        nonlocal cur
        if cur and (cur["headers"] or cur["bullets"] or cur["start"]):
            entries.append(cur)
        cur = None

    for raw in lines:
        line = _clean(raw)
        if not line:
            continue
        if _is_bullet(raw):
            text = _strip_bullet(raw)
            if cur is None:
                cur = new()
            if text:
                cur["bullets"].append(text)
            continue

        lab = re.match(r"^(company|employer|organi[sz]ation|position|job title|title|role|designation|"
                       r"period|duration|dates?|location|duties|responsibilities|key responsibilities|"
                       r"achievements|key achievements|reason for leaving)\s*[:\-–]\s*(.*)$", line, re.I)
        if lab:
            key, val = lab.group(1).lower(), lab.group(2).strip()
            if key in ("company", "employer", "organisation", "organization"):
                if cur and (cur["labelled"].get("employer") or cur["bullets"]):
                    flush()
                cur = cur or new()
                cur["labelled"]["employer"] = val
            elif key in ("position", "job title", "title", "role", "designation"):
                if cur and (cur["labelled"].get("position") or cur["bullets"]):
                    flush()
                cur = cur or new()
                cur["labelled"]["position"] = val
            elif key in ("period", "duration", "date", "dates"):
                cur = cur or new()
                rng = DATE_RANGE.search(val)
                if rng:
                    cur["start"], cur["end"] = norm_date(rng.group(1)), norm_date(rng.group(2))
                    cur["date_text"] = rng.group(0)
            elif key == "location":
                cur = cur or new()
                cur["location"] = val
            elif key == "reason for leaving":
                pass  # outdated convention, dropped (flagged by the sensitive-data scan)
            elif val:
                cur = cur or new()
                cur["bullets"].append(val)
            continue

        rng = DATE_RANGE.search(line)
        if rng:
            rest = _clean((line[:rng.start()] + " " + line[rng.end():]).strip(" ,|-–—()"))
            if cur and (cur["bullets"] or cur["start"]):
                flush()
            cur = cur or new()
            cur["start"], cur["end"] = norm_date(rng.group(1)), norm_date(rng.group(2))
            cur["is_current"] = cur["end"] == "Present"
            cur["date_text"] = rng.group(0)
            if rest:
                cur["headers"].append(rest)
            continue

        words = line.split()
        long_sentence = len(words) > 12 or (line.endswith(".") and len(words) > 7)
        if long_sentence:
            if cur is None:
                cur = new()
            cur["bullets"].append(line)
            continue
        # A short header-like line.
        if cur and (cur["bullets"] or (len(cur["headers"]) >= 2 and cur["start"])):
            flush()
        cur = cur or new()
        cur["headers"].append(line)
    flush()

    out = []
    for e in entries:
        position, employer, location, needs_review = _resolve_headers(e)
        out.append({
            "position": position, "employer": employer, "location": location or e.get("location"),
            "start": e["start"], "end": e["end"], "is_current": e["is_current"] or (e["end"] == "Present"),
            "bullets": e["bullets"], "needs_review": needs_review,
        })
    return out


def _resolve_headers(e: dict) -> tuple[str | None, str | None, str | None, bool]:
    position = e["labelled"].get("position")
    employer = e["labelled"].get("employer")
    location = None
    unresolved: list[str] = []
    for h in e["headers"]:
        pieces = _split_pieces(h)
        for p in pieces:
            if not p:
                continue
            if _looks_place(p) and location is None:
                location = p
            elif _looks_role(p) and not position:
                position = p
            elif _looks_org(p) and not employer:
                employer = p
            else:
                unresolved.append(p)
    needs_review = False
    for p in unresolved:
        if not position:
            position = p
            needs_review = True
        elif not employer:
            employer = p
            needs_review = True
    if not position or not employer:
        needs_review = True
    return position, employer, location, needs_review


def _edu_status(text: str, end_year: int | None, open_ended: bool) -> str:
    if AWAITING.search(text):
        return "awaiting_conferral"
    if open_ended or IN_PROGRESS.search(text):
        return "in_progress"
    if COMPLETED.search(text):
        return "completed"
    if end_year:
        return "completed" if end_year < date.today().year else "unverified"
    return "unverified"


def _parse_education(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    cur: dict | None = None
    pending_inst: str | None = None

    def flush():
        nonlocal cur
        if cur:
            entries.append(cur)
        cur = None

    for raw in lines:
        line = _strip_bullet(raw) if _is_bullet(raw) else _clean(raw)
        if not line:
            continue
        rng = DATE_RANGE.search(line)
        single = SINGLE_DATE.findall(line) if not rng else []
        body = line
        date_text = None
        if rng:
            date_text = f"{norm_date(rng.group(1))} – {norm_date(rng.group(2))}"
            body = _clean(line[:rng.start()] + " " + line[rng.end():])
        elif single:
            date_text = norm_date(single[-1])
            body = _clean(re.sub(SINGLE_DATE, "", line))
        body = body.strip(" ,|-–—()")
        is_qual = bool(QUAL_WORDS.search(body))
        is_inst = bool(INSTITUTION_WORDS.search(body))

        if is_qual:
            pieces = _split_pieces(body)
            qual = body
            inst = None
            if len(pieces) > 1:
                q = [p for p in pieces if QUAL_WORDS.search(p)]
                i = [p for p in pieces if INSTITUTION_WORDS.search(p) and not QUAL_WORDS.search(p)]
                if q:
                    qual = q[0] if len(q) == 1 else " – ".join(q)
                if i:
                    inst = i[0]
            if cur and cur.get("qualification"):
                flush()
            cur = cur or {"qualification": None, "institution": None, "date_text": None, "notes": []}
            cur["qualification"] = re.sub(r"\s*\((?:in progress|current|completed|ongoing)\)\s*$", "",
                                          qual, flags=re.I).strip(" ,;:-–—")
            cur["institution"] = cur.get("institution") or inst or pending_inst
            pending_inst = None
            if date_text:
                cur["date_text"] = date_text
            cur["notes"].append(line)
        elif is_inst:
            inst = body
            if cur and not cur.get("institution"):
                cur["institution"] = inst
                if date_text and not cur.get("date_text"):
                    cur["date_text"] = date_text
                cur["notes"].append(line)
            else:
                flush()
                pending_inst = inst
                cur = {"qualification": None, "institution": inst, "date_text": date_text, "notes": [line]}
        elif cur:
            if date_text and not cur.get("date_text"):
                cur["date_text"] = date_text
            cur["notes"].append(line)
    flush()

    out = []
    for e in entries:
        if not e.get("qualification") and not e.get("institution"):
            continue
        notes = " ".join(e.get("notes", []))
        dt = e.get("date_text")
        open_ended = bool(dt and "Present" in dt)
        end_year = year_of(dt.split("–")[-1]) if dt else None
        status = _edu_status(notes, end_year, open_ended)
        out.append({
            "qualification": e.get("qualification"), "institution": e.get("institution"),
            "date_text": dt, "year": end_year, "status": status,
            "nqf": (re.search(r"NQF\s*(?:level)?\s*(\d{1,2})", notes, re.I) or [None, None])[1],
        })
    return out


def _parse_certifications(lines: list[str], default_kind: str = "certification") -> list[dict]:
    out = []
    for raw in lines:
        line = _strip_bullet(raw) if _is_bullet(raw) else _clean(raw)
        if len(line) < 3:
            continue
        single = SINGLE_DATE.findall(line)
        year = norm_date(single[-1]) if single else None
        body = _clean(re.sub(SINGLE_DATE, "", line)).strip(" ,|-–—()") if single else line
        status = "in_progress" if IN_PROGRESS.search(line) else "completed"
        body = _clean(re.sub(r"\s*[-–—(,]*\s*(?:in progress|ongoing|currently studying|current|completed)\s*\)?\s*$",
                             "", body, flags=re.I))
        issuer = None
        m = re.search(r"\(([A-Z][A-Za-z&.\- ]{1,60})\)\s*$", body)
        if m and (m.group(1).isupper() or INSTITUTION_WORDS.search(m.group(1)) or _looks_org(m.group(1))):
            issuer = m.group(1).strip()
            body = body[:m.start()].strip()
        pieces = _split_pieces(body)
        name = body
        if len(pieces) == 2 and (INSTITUTION_WORDS.search(pieces[1]) or _looks_org(pieces[1])
                                 or pieces[1].isupper()):
            name, issuer = pieces
        low = line.lower()
        kind = default_kind
        if re.search(r"\bregist(?:ered|ration)\b|\bsacnasp\b|\becsa\b|\bhpcsa\b|\bsaimm\b|\bsaiche\b", low):
            kind = "registration"
        elif re.search(r"\bmember(?:ship)?\b|\baffiliate\b|\bfellow\b", low):
            kind = "membership"
        elif re.search(r"\bcourse\b|\bworkshop\b|\btraining\b|\binduction\b|\bseminar\b|\bwebinar\b", low):
            kind = "short_course"
        out.append({"name": name, "issuer": issuer, "year": year, "kind": kind, "status": status})
    return out


_SKILL_SPLIT = re.compile(r"\s*(?:,|;|\||•|·|▪|•|\t| {3,}| / )\s*")
_RATING = re.compile(r"[★☆●○◆◇■□]+|\(\s*\d+\s*/\s*\d+\s*\)|\b\d\s*/\s*(?:5|10)\b|\d{2,3}\s*%")


def _parse_list(lines: list[str]) -> list[str]:
    items: list[str] = []
    for raw in lines:
        line = _strip_bullet(raw) if _is_bullet(raw) else _clean(raw)
        line = _clean(_RATING.sub("", line))
        if not line:
            continue
        m = re.match(r"^([A-Za-z &/'-]{3,35}):\s*(.+)$", line)
        if m:  # "Technical: SCADA, LIMS"
            line = m.group(2)
        parts = _SKILL_SPLIT.split(line) if (len(line.split()) > 6 or re.search(r"[,;|•]", line)) else [line]
        for p in parts:
            p = p.strip(" .-–—:")
            if 2 <= len(p) <= 70 and not re.fullmatch(r"(?:basic|intermediate|advanced|expert|good|excellent|fluent)", p, re.I):
                items.append(p)
    seen = set()
    out = []
    for i in items:
        k = i.lower()
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


_REF_LABEL = re.compile(r"^\s*(name|referee|contact person|position|title|designation|relationship|company|"
                        r"organi[sz]ation|employer|tel(?:ephone)?|phone|cell(?:phone)?|mobile|contact(?: no| number)?|"
                        r"e-?mail)\s*[:\-–]\s*(.+)$", re.I)
_REF_ON_REQUEST = re.compile(r"\b(?:available|furnished|provided)\s+(?:up)?on\s+request\b", re.I)


def _parse_references(lines: list[str]) -> tuple[list[dict], bool]:
    """Referees as {name, details, phone, email}. Returns (referees, 'available on request')."""
    refs: list[dict] = []
    cur: dict | None = None
    on_request = False

    def flush():
        nonlocal cur
        if cur and (cur["name"] or cur["phone"] or cur["email"]):
            cur["details"] = ", ".join(d for d in cur["details"] if d)
            name = cur["name"] or ""
            plausible = bool(cur["phone"] or cur["email"]) or bool(
                re.match(r"(?i)^(?:mr|mrs|ms|miss|dr|prof|rev|adv)\.?\s", name)) or _looks_like_name(name)
            # Text that drifted under the heading (e.g. a skills table a DOCX
            # extractor appends at the end) is not a referee.
            if plausible:
                refs.append(cur)
        cur = None

    def new():
        return {"name": None, "details": [], "phone": None, "email": None}

    for raw in lines:
        line = _strip_bullet(raw) if _is_bullet(raw) else _clean(raw)
        if not line:
            continue
        if _REF_ON_REQUEST.search(line):
            on_request = True
            continue
        m = _REF_LABEL.match(line)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key in ("name", "referee", "contact person"):
                if cur and (cur["name"] or cur["phone"]):
                    flush()
                cur = cur or new()
                cur["name"] = val
            elif key.startswith(("tel", "phone", "cell", "mobile", "contact")):
                cur = cur or new()
                ph = PHONE.search(val)
                cur["phone"] = _clean(ph.group(0)) if ph else val
            elif key.startswith(("e-mail", "email", "e mail")) or "mail" in key:
                cur = cur or new()
                em = EMAIL.search(val)
                cur["email"] = em.group(0) if em else val
            else:
                cur = cur or new()
                cur["details"].append(val)
            continue
        em = EMAIL.search(line)
        ph = PHONE.search(line)
        rest = line
        if em:
            rest = rest.replace(em.group(0), " ")
        if ph:
            rest = rest.replace(ph.group(0), " ")
        rest = re.sub(r"\b(?:tel|cell|phone|mobile|e-?mail|contact)\b\s*[:.]?", " ", rest, flags=re.I)
        pieces = [p.strip(" ,;|-–—:()") for p in re.split(r"\s*[,|;]\s*|\s[–—-]\s", rest) if p.strip(" ,;|-–—:()")]
        if cur and (cur["phone"] or cur["email"]) and pieces and cur["name"]:
            flush()  # contact details close a referee; a new named line starts the next one
        cur = cur or new()
        if pieces:
            if not cur["name"]:
                cur["name"] = pieces[0]
                cur["details"] += pieces[1:]
            else:
                cur["details"] += pieces
        if ph and not cur["phone"]:
            cur["phone"] = _clean(ph.group(0))
        if em and not cur["email"]:
            cur["email"] = em.group(0)
    flush()
    return refs[:5], on_request


def parse_cv_text(text: str) -> dict:
    raw_lines = normalise_lines(text.splitlines())
    sections, headings = _sections(raw_lines)

    cv: dict = {
        "full_name": None, "headline": None, "email": None, "phone": None, "location": None,
        "linkedin_url": None, "links": [], "summary": None, "skills": [], "software": [],
        "experience": [], "education": [], "certifications": [], "languages": [],
        "drivers_licence": None, "projects": [], "achievements": [], "memberships": [], "interests": [],
        "sensitive": [], "references_present": False, "references": [], "references_on_request": False,
        "headings": headings,
    }

    # ---- Contact (anywhere in the document) ----
    em = EMAIL.search(text)
    cv["email"] = em.group(0) if em else None
    li = LINKEDIN.search(text)
    cv["linkedin_url"] = li.group(0).rstrip(".") if li else None
    # Referees' numbers are not the candidate's: skip those sections.
    referee_text = {x for canon, body in sections if canon == "references" for x in body}
    for raw in raw_lines:
        if cv["phone"]:
            break
        if raw in referee_text:
            continue
        if SA_ID.search(raw) and re.search(r"\bid\b|identity", raw, re.I):
            continue
        for m in PHONE.finditer(raw):
            digits = re.sub(r"\D", "", m.group(0))
            if 9 <= len(digits) <= 13 and not SA_ID.fullmatch(m.group(0).replace(" ", "")):
                cv["phone"] = _clean(m.group(0))
                break
    for u in URL.findall(text):
        if "linkedin.com" not in u.lower() and "@" not in u and u.rstrip(".") not in cv["links"]:
            cv["links"].append(u.rstrip("."))
    cv["links"] = cv["links"][:3]

    # ---- Personal-detail labels & sensitive data (anywhere) ----
    for raw in raw_lines:
        line = _clean(raw)
        if not line:
            continue
        for kind, rx in _SENSITIVE_RE.items():
            if rx.match(line):
                if kind == "home_address":
                    m = rx.match(line)
                    parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
                    places = [p for p in parts if _looks_place(p)]
                    if places and not cv["location"]:
                        cv["location"] = ", ".join(places[:2])
                if kind == "marital_status" and not re.match(r"^\s*marital", line, re.I):
                    continue
                if kind not in {s["kind"] for s in cv["sensitive"]}:
                    cv["sensitive"].append({"kind": kind, "label": SENSITIVE_LABEL_TEXT[kind]})
                break
        if SA_ID.search(line) and re.search(r"\bid\b|identity", line, re.I) \
                and "id_number" not in {s["kind"] for s in cv["sensitive"]}:
            cv["sensitive"].append({"kind": "id_number", "label": SENSITIVE_LABEL_TEXT["id_number"]})
        m = _DRIVERS.match(line)
        if m and not cv["drivers_licence"]:
            val = m.group(1).strip(" :-–")
            cv["drivers_licence"] = f"Code {val}" if re.fullmatch(r"(?:code\s*)?(?:A1?|B|C1?|EB|EC1?)", val, re.I) \
                and not val.lower().startswith("code") else (val or "Yes")
        m = _LANG_LABEL.match(line)
        if m:
            cv["languages"] += [x for x in _parse_list([m.group(1)]) if x not in cv["languages"]]
        m = _NAME_LABEL.match(line)
        if m and not cv["full_name"] and not EMAIL.search(m.group(1)):
            cv["full_name"] = m.group(1).strip()
        m = _SURNAME_LABEL.match(line)
        if m and cv["full_name"] and m.group(1).strip().lower() not in cv["full_name"].lower():
            cv["full_name"] = f"{cv['full_name']} {m.group(1).strip()}"
        m = _LOCATION_LABEL.match(line)
        if m and not cv["location"]:
            cv["location"] = m.group(1).strip()

    # ---- Header block: name, headline, early summary ----
    header = [_clean(x) for x in sections[0][1] if _clean(x)]
    for line in header[:4]:
        if not cv["full_name"] and _looks_like_name(line):
            cv["full_name"] = _title_case_name(line)
            break
    header_rest = [ln for ln in header if ln != cv["full_name"] and _title_case_name(ln) != cv["full_name"]]
    for ln in header_rest[:4]:
        if EMAIL.search(ln) or PHONE.search(ln) or URL.search(ln) or ":" in ln:
            continue
        if _looks_place(ln):
            cv["location"] = cv["location"] or ln
            continue
        if len(ln.split()) <= 12 and not ln.endswith(".") and not cv["headline"]:
            cv["headline"] = ln.strip(" |")
    loose = [ln for ln in header_rest if len(ln.split()) > 12 and not EMAIL.search(ln)]
    if loose:
        cv["summary"] = " ".join(loose)
    if not cv["location"]:
        for ln in header_rest[:6]:
            for piece in re.split(r"\s*[|•·]\s*", ln):
                if _looks_place(piece):
                    cv["location"] = piece.strip()
                    break

    # ---- Sections ----
    for canon, body in sections[1:]:
        if canon == "summary":
            txt = " ".join(_strip_bullet(b) if _is_bullet(b) else _clean(b) for b in body if _clean(b))
            if txt:
                cv["summary"] = txt if not cv["summary"] else f"{cv['summary']} {txt}"
        elif canon == "skills":
            cv["skills"] += _parse_list(body)
        elif canon == "software":
            cv["software"] += _parse_list(body)
        elif canon == "experience":
            cv["experience"] += _parse_experience(body)
        elif canon == "education":
            cv["education"] += _parse_education(body)
        elif canon == "certifications":
            cv["certifications"] += _parse_certifications(body)
        elif canon == "memberships":
            cv["memberships"] += [c["name"] for c in _parse_certifications(body, "membership")]
        elif canon == "projects":
            cv["projects"] += [_strip_bullet(b) if _is_bullet(b) else _clean(b) for b in body if _clean(b)]
        elif canon == "achievements":
            cv["achievements"] += [_strip_bullet(b) if _is_bullet(b) else _clean(b) for b in body if _clean(b)]
        elif canon == "languages":
            cv["languages"] += [x for x in _parse_list(body) if x not in cv["languages"]]
        elif canon == "references":
            refs, on_request = _parse_references(body)
            cv["references"] += refs
            cv["references_on_request"] = cv["references_on_request"] or on_request
            cv["references_present"] = bool(cv["references"]) or on_request
        elif canon == "interests":
            cv["interests"] += _parse_list(body)

    # Skill lists sometimes carry languages/licences — move them.
    lang_words = {"english", "afrikaans", "isizulu", "zulu", "xhosa", "isixhosa", "sesotho", "sotho", "setswana",
                  "tswana", "sepedi", "venda", "tshivenda", "xitsonga", "tsonga", "siswati", "swati", "isindebele",
                  "ndebele", "french", "portuguese", "swahili", "kiswahili", "german", "spanish", "chinese", "arabic"}
    keep = []
    for s in cv["skills"]:
        if s.lower().split(" (")[0].strip() in lang_words:
            if s not in cv["languages"]:
                cv["languages"].append(s)
        else:
            keep.append(s)
    cv["skills"] = keep
    # Experience entries with no recognisable header at all are probably a parse
    # artefact (e.g. a stray bullet before the first role).
    cv["experience"] = [e for e in cv["experience"] if e["position"] or e["employer"] or len(e["bullets"]) >= 2]
    return cv
