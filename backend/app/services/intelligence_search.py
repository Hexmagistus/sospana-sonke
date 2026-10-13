"""Deterministic question search over the employer directory and stored roles.

No language model. A question is turned into filters, then counted and listed
from rows we already hold. The wording of the answer is a template filled with
those counts. When the question asks for a dataset we do not have, the answer
says so and does not invent a figure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, defer

from app.core.config import settings
from app.models.company import Company
from app.models.vacancy import Vacancy
from app.scraper.extract import SA_PROVINCES, _CITY_TO_PROVINCE
from app.services.category_groups import stored_values_for
from app.services.country_names import COUNTRY_ALIASES, NON_COUNTRY_BUCKETS, canonical_country
from app.services.labour_stats import latest_rate, load_table, place_row
from app.services.vacancy_counts import companies_with_known_vacancy_count, open_vacancy_counts

SAMPLE = 8
_COUNTRY_TTL = 300.0
_country_cache: dict = {"at": 0.0, "names": None}

# Whole-word aliases. Applied only when the canonical country is actually in
# the directory, so a short token cannot invent a country we do not list.
_EXTRA_ALIASES: tuple[tuple[str, str], ...] = (
    ("sa", "South Africa"),
    ("uk", "United Kingdom"),
    ("usa", "United States"),
    ("uae", "United Arab Emirates"),
)

_PROVINCE_ALIASES: tuple[tuple[str, str], ...] = (
    ("kwazulu-natal", "KwaZulu-Natal"),
    ("kwazulu natal", "KwaZulu-Natal"),
    ("kzn", "KwaZulu-Natal"),
    *((name.lower(), name) for name in SA_PROVINCES),
)

# Cities the scraper already maps. Ambiguous ones ("george", "newcastle") count
# only when the question says "in/near/around", so a person's name is not a city.
_AMBIGUOUS_CITIES = frozenset({"george", "newcastle"})

# Longer phrases first. Codes are expanded to every stored source_type alias.
_CATEGORIES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("state-owned enterprises", ("SOE",), "state-owned enterprises"),
    ("state owned enterprises", ("SOE",), "state-owned enterprises"),
    ("state-owned", ("SOE",), "state-owned enterprises"),
    ("state owned", ("SOE",), "state-owned enterprises"),
    ("parastatals", ("SOE",), "state-owned enterprises"),
    ("parastatal", ("SOE",), "state-owned enterprises"),
    ("listed companies", ("JSE",), "listed companies"),
    ("municipalities", ("MUNI",), "municipalities"),
    ("municipality", ("MUNI",), "municipalities"),
    ("universities", ("UNI",), "universities"),
    ("university", ("UNI",), "universities"),
    ("private companies", ("PRIVATE",), "private companies"),
    ("private employers", ("PRIVATE",), "private companies"),
    ("colleges", ("COLLEGE",), "colleges"),
    ("college", ("COLLEGE",), "colleges"),
    ("hospitals", ("HOSPITAL",), "hospitals"),
    ("hospital", ("HOSPITAL",), "hospitals"),
    ("non-profits", ("NGO",), "NGOs"),
    ("nonprofits", ("NGO",), "NGOs"),
    ("ngos", ("NGO",), "NGOs"),
    ("ngo", ("NGO",), "NGOs"),
    ("government departments", ("DEPT",), "government departments"),
    ("government", ("DEPT", "MUNI", "SOE"), "government"),
    ("departments", ("DEPT",), "government departments"),
    ("ministries", ("DEPT",), "government departments"),
    ("ministry", ("DEPT",), "government departments"),
    ("setas", ("SETA",), "SETAs"),
    ("seta", ("SETA",), "SETAs"),
    ("jse", ("JSE",), "listed companies"),
)

# Topics this database cannot answer. The phrase is removed from the keyword
# search and named in the answer. Nothing is estimated in its place.
_DECLINED: tuple[tuple[str, str], ...] = (
    ("unemployment rate", "an unemployment rate"),
    ("unemployment", "an unemployment rate"),
    ("unemployed", "an unemployment rate"),
    ("municipal budget", "municipal budgets"),
    ("election results", "election results"),
    ("procurement", "procurement spend"),
    ("crime rate", "a crime rate"),
    ("stats sa", "Stats SA tables"),
    ("inflation", "inflation"),
    ("population", "population figures"),
    ("census", "a census"),
    ("gdp", "GDP"),
    ("ward", "ward-level data"),
)

_STEMS = {
    "nurses": "nurse",
    "nursing": "nurse",
    "interns": "intern",
    "internship": "intern",
    "internships": "intern",
    "learnerships": "learnership",
    "bursaries": "bursary",
    "scholarships": "scholarship",
}

_EMPLOYMENT = {
    "intern": "intern",
    "internship": "intern",
    "internships": "intern",
    "learnership": "learnership",
    "learnerships": "learnership",
    "permanent": "permanent",
    "contract": "contract",
    "bursary": "bursary",
    "bursaries": "bursary",
    "scholarship": "scholarship",
    "scholarships": "scholarship",
}

_WORK_MODE = {
    "remote": "remote",
    "hybrid": "hybrid",
    "on-site": "onsite",
    "onsite": "onsite",
}

_STOP = frozenset({
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "me", "my",
    "show", "find", "search", "what", "which", "are", "is", "there", "any", "please",
    "jobs", "job", "roles", "role", "vacancies", "vacancy", "openings", "opening",
    "opportunities", "opportunity", "employers", "employer", "companies", "company",
    "careers", "career", "page", "pages", "link", "links", "with", "stored", "open",
    "how", "many", "does", "do", "have", "has", "list", "near", "around", "who",
    "hiring", "tell", "about", "from", "that", "this", "can", "i", "we", "you",
    "want", "looking", "seek", "seeking", "available", "current", "currently",
})

_BASE_LIMITS = (
    "These figures are roles and employers stored by Sospana Sonke, not every vacancy in a country.",
    "A missing role does not mean the employer has no openings. Check the careers page.",
    "The advert text is not included. Open the source link to read the role.",
    "Last seen is the last scan that found the role. It is not a promise the role is still open.",
    "An optional language-model layer is disabled. This answer is a filter and a count, not a generated explanation.",
    "A careers link may be the employer's main board, not a list filtered to one country.",
)


@dataclass
class Understood:
    keywords: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    employer: str | None = None
    source_types: tuple[str, ...] = ()
    source_label: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    max_age_days: int | None = None
    careers_link_only: bool = False
    looking_for: str = "both"
    declined: tuple[str, ...] = ()
    prompt: bool = False
    supported: bool = True

    def has_filter(self) -> bool:
        return bool(
            self.keywords or self.country or self.province or self.city or self.employer
            or self.source_types or self.employment_type or self.work_mode or self.careers_link_only
        )


@dataclass
class IntelligenceAnswer:
    question: str
    understood: Understood
    llm: str = "disabled"
    enough_data: bool = False
    summary: str = ""
    reading: str = ""
    limitations: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    vacancies: list[dict] = field(default_factory=list)
    vacancy_count: int = 0
    employers: list[dict] = field(default_factory=list)
    employer_count: int = 0
    with_link_count: int = 0
    counted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_id: str | None = None
    citation: dict | None = None


def _like(value: str) -> str:
    cleaned = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{cleaned}%"


def _contained(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text, flags=re.IGNORECASE) is not None


def _cut(text: str, phrase: str) -> str:
    return re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", text, count=1, flags=re.IGNORECASE)


def _original_slice(raw: str, phrase: str) -> str:
    match = re.search(re.escape(phrase), raw, flags=re.IGNORECASE)
    return " ".join(match.group(0).split()) if match else phrase


def _expand_types(codes: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for code in codes:
        for value in stored_values_for(code):
            if value not in out:
                out.append(value)
        if code not in out:
            out.append(code)
    return tuple(out)


def load_country_names(db: Session) -> list[str]:
    """Distinct directory countries, canonical spelling, buckets excluded."""
    now = datetime.now(timezone.utc).timestamp()
    cached = _country_cache["names"]
    if settings.ENV != "test" and cached is not None and now - _country_cache["at"] < _COUNTRY_TTL:
        return cached
    rows = (
        db.query(Company.country)
        .filter(Company.deleted_at.is_(None), Company.country.isnot(None), Company.country != "")
        .distinct()
        .all()
    )
    names: list[str] = []
    seen: set[str] = set()
    for (name,) in rows:
        canon = canonical_country(name)
        if not canon or canon in NON_COUNTRY_BUCKETS or canon in seen:
            continue
        seen.add(canon)
        names.append(canon)
    if settings.ENV != "test":
        _country_cache["names"] = names
        _country_cache["at"] = now
    return names


def _country_phrases(names: list[str]) -> list[tuple[str, str]]:
    present = {name.lower(): name for name in names}
    phrases: list[tuple[str, str]] = [(name.lower(), name) for name in names]
    for alias, target in (*COUNTRY_ALIASES.items(), *_EXTRA_ALIASES):
        canon = canonical_country(target)
        if canon.lower() in present:
            phrases.append((alias.lower(), present[canon.lower()]))
    # Longest phrase wins so "equatorial guinea" beats "guinea".
    phrases.sort(key=lambda item: len(item[0]), reverse=True)
    return phrases


def parse_question(question: str, country_names: list[str]) -> Understood:
    raw = " ".join((question or "").strip().split())
    if not raw:
        return Understood(prompt=True, supported=False, looking_for="both")
    raw = raw[:200]
    text = raw.lower().replace("'s", " ").replace("’s", " ")
    text = re.sub(r"[?!,;:]+", " ", text)
    text = " ".join(text.split())

    declined: list[str] = []
    for phrase, label in _DECLINED:
        if _contained(text, phrase):
            declined.append(label)
            text = _cut(text, phrase)

    max_age: int | None = None
    age = re.search(r"\b(?:in the )?(?:last|past)\s+(\d+)\s+days?\b", text)
    if age:
        max_age = max(1, min(365, int(age.group(1))))
        text = _cut(text, age.group(0))
    elif _contained(text, "today"):
        max_age = 1
        text = _cut(text, "today")
    elif _contained(text, "this week") or _contained(text, "last week"):
        max_age = 7
        text = _cut(text, "this week")
        text = _cut(text, "last week")
    elif _contained(text, "last month") or _contained(text, "this month"):
        max_age = 30
        text = _cut(text, "last month")
        text = _cut(text, "this month")

    province = None
    for phrase, canon in sorted(_PROVINCE_ALIASES, key=lambda item: len(item[0]), reverse=True):
        if _contained(text, phrase):
            province = canon
            text = _cut(text, phrase)
            break

    city = None
    cities = sorted({name for name in _CITY_TO_PROVINCE}, key=len, reverse=True)
    for phrase in cities:
        preceded = re.search(rf"(?<!\w)(?:in|near|around)\s+{re.escape(phrase)}(?!\w)", text)
        bare = phrase not in _AMBIGUOUS_CITIES and _contained(text, phrase)
        if preceded or bare:
            city = phrase.title()
            text = _cut(text, phrase)
            break

    country = None
    for phrase, canon in _country_phrases(country_names):
        if _contained(text, phrase):
            country = canon
            text = _cut(text, phrase)
            break

    source_types: tuple[str, ...] = ()
    source_label = None
    for phrase, codes, label in _CATEGORIES:
        if _contained(text, phrase):
            source_types = _expand_types(codes)
            source_label = label
            text = _cut(text, phrase)
            break

    careers_link_only = False
    if re.search(r"\bcareers?\s+links?\b", text):
        careers_link_only = True
        text = re.sub(r"\bcareers?\s+links?\b", " ", text)

    asks_roles = bool(re.search(
        r"\b(jobs?|roles?|vacancies|vacancy|openings?|internships?|learnerships?|bursar(?:y|ies)|scholarships?)\b",
        text,
    ))
    asks_employers = careers_link_only or bool(re.search(r"\b(employers?|companies|hiring)\b", text))

    employer = None
    at = re.search(r"\bat\s+(.+)$", text)
    if at:
        name = re.split(r"\b(?:in|with|for|and)\b", at.group(1))[0].strip(" .")
        words = [w for w in name.split() if w not in _STOP]
        if words:
            employer = _original_slice(raw, " ".join(words))
            text = text[:at.start()]

    employment = None
    work_mode = None
    kept: list[str] = []
    for word in text.split():
        if word in _WORK_MODE and work_mode is None:
            work_mode = _WORK_MODE[word]
            continue
        if word in _EMPLOYMENT and employment is None:
            employment = _EMPLOYMENT[word]
            continue
        if word in _STOP or len(word) < 2:
            continue
        kept.append(_STEMS.get(word, word))
    keywords = " ".join(kept) or None
    if employment and keywords and employment in keywords.split():
        # The title search already includes this word. A second employment-type
        # filter would drop roles whose type was never filled in.
        employment = None

    if source_label and not asks_roles:
        looking_for = "employers"
    elif asks_employers and not asks_roles:
        looking_for = "employers"
    elif asks_roles and not asks_employers:
        looking_for = "roles"
    else:
        looking_for = "both"

    understood = Understood(
        keywords=keywords,
        country=country,
        province=province,
        city=city,
        employer=employer,
        source_types=source_types,
        source_label=source_label,
        employment_type=employment,
        work_mode=work_mode,
        max_age_days=max_age,
        careers_link_only=careers_link_only,
        looking_for=looking_for,
        declined=tuple(declined),
        supported=True,
    )
    if not understood.has_filter():
        understood.supported = False
    return understood


def _apply_company_filters(query, understood: Understood, *, name_keyword: bool):
    if understood.country:
        from app.services.country_names import spellings_for
        query = query.filter(Company.country.in_(spellings_for(understood.country)))
    if understood.employer:
        query = query.filter(Company.company_name.ilike(_like(understood.employer), escape="\\"))
    if understood.source_types:
        query = query.filter(func.upper(Company.source_type).in_(understood.source_types))
    if understood.careers_link_only:
        query = query.filter(Company.careers_url.isnot(None), Company.careers_url != "")
    if name_keyword and understood.keywords:
        query = query.filter(Company.company_name.ilike(_like(understood.keywords), escape="\\"))
    return query


def _vacancy_query(db: Session, understood: Understood):
    """Open, unexpired roles. A country matches the employer or the role.

    An employer-directory question does not also require the category word in
    the job title. A role question puts each title word on the vacancy, not on
    the employer name.
    """
    today = date.today()
    query = (
        db.query(Vacancy, Company)
        .join(Company, Company.id == Vacancy.company_id)
        .options(
            defer(Vacancy.description),
            defer(Vacancy.raw_content),
            defer(Vacancy.requirements_text),
            defer(Vacancy.qualifications),
            defer(Vacancy.experience),
            defer(Company.notes),
            defer(Company.favicon_data),
        )
        .filter(Vacancy.deleted_at.is_(None), Company.deleted_at.is_(None))
        .filter(Vacancy.is_open.is_(True))
        .filter(or_(Vacancy.closing_date.is_(None), Vacancy.closing_date >= today))
    )
    narrowed = replace(understood, country=None, keywords=None)
    query = _apply_company_filters(query, narrowed, name_keyword=False)
    if understood.country:
        from app.services.country_names import spellings_for
        names = spellings_for(understood.country)
        query = query.filter(or_(Company.country.in_(names), Vacancy.country.in_(names)))
    if understood.looking_for != "employers" and understood.keywords:
        for word in understood.keywords.split():
            query = query.filter(Vacancy.title.ilike(_like(word), escape="\\"))
    if understood.employment_type:
        query = query.filter(or_(
            Vacancy.employment_type.ilike(_like(understood.employment_type), escape="\\"),
            Vacancy.title.ilike(_like(understood.employment_type), escape="\\"),
        ))
    if understood.work_mode:
        query = query.filter(or_(
            Vacancy.work_mode.ilike(_like(understood.work_mode), escape="\\"),
            Vacancy.title.ilike(_like(understood.work_mode), escape="\\"),
        ))
    if understood.province:
        query = query.filter(Vacancy.province == understood.province)
    if understood.city:
        query = query.filter(or_(
            Vacancy.location.ilike(_like(understood.city), escape="\\"),
            Vacancy.city.ilike(_like(understood.city), escape="\\"),
        ))
    if understood.max_age_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=understood.max_age_days)
        query = query.filter(Vacancy.last_seen_at >= cutoff)
    return query


def _employer_query(db: Session, understood: Understood):
    query = (
        db.query(Company)
        .options(
            defer(Company.notes),
            defer(Company.favicon_data),
            defer(Company.favicon_mime),
            defer(Company.last_final_url),
            defer(Company.content_hash),
        )
        .filter(Company.deleted_at.is_(None))
    )
    # Employer directory search does not repeat the role keyword onto the name
    # when the visitor asked for roles. "Both" and "employers" do.
    return _apply_company_filters(
        query,
        understood,
        name_keyword=understood.looking_for != "roles",
    )


def _public_vacancy(vacancy: Vacancy, company: Company) -> dict:
    return {
        "id": vacancy.id,
        "company_id": company.id,
        "title": vacancy.title,
        "company_name": company.company_name,
        "company_country": company.country,
        "location": vacancy.location,
        "country": vacancy.country,
        "employment_type": vacancy.employment_type,
        "work_mode": vacancy.work_mode,
        "salary": vacancy.salary,
        "salary_min": vacancy.salary_min,
        "salary_max": vacancy.salary_max,
        "salary_currency": vacancy.salary_currency,
        "posting_date": vacancy.posting_date,
        "closing_date": vacancy.closing_date,
        "first_seen_at": vacancy.first_seen_at,
        "last_seen_at": vacancy.last_seen_at,
        "application_url": vacancy.application_url or vacancy.canonical_url or vacancy.source_url,
        "is_open": vacancy.is_open,
    }


def _public_employer(company: Company, counts: dict[str, int], known: set[str]) -> dict:
    n = counts.get(company.id, 0)
    url = (company.careers_url or "").strip() or None
    return {
        "id": company.id,
        "company_name": company.company_name,
        "country": company.country,
        "source_type": company.source_type,
        "careers_url": url,
        "last_checked": company.last_checked,
        "url_looks_like_careers": company.url_looks_like_careers,
        "open_vacancies": n,
        "open_vacancies_known": n > 0 or company.id in known,
    }


def _reading(understood: Understood) -> str:
    if understood.prompt:
        return "Type a question to search the directory and the stored roles."
    if not understood.supported:
        return "This question does not map to a role, an employer, or a country we store."
    parts: list[str] = []
    if understood.keywords:
        parts.append(f"Title words: “{understood.keywords}”.")
    if understood.employer:
        parts.append(f"Employer name contains “{understood.employer}”.")
    if understood.source_label:
        parts.append(f"Category: {understood.source_label}.")
    if understood.country:
        parts.append(f"Country: {understood.country}.")
    if understood.province:
        parts.append(f"Province: {understood.province}.")
    if understood.city:
        parts.append(f"City in the location text: {understood.city}.")
    if understood.employment_type:
        parts.append(f"Employment type contains “{understood.employment_type}”.")
    if understood.work_mode:
        parts.append(f"Work mode contains “{understood.work_mode}”.")
    if understood.max_age_days:
        parts.append(f"Last seen within {understood.max_age_days} days.")
    if understood.careers_link_only:
        parts.append("Only employers with a careers link stored.")
    if understood.looking_for == "roles":
        parts.append("Searching stored roles.")
    elif understood.looking_for == "employers":
        parts.append("Searching the employer directory.")
    else:
        parts.append("Searching stored roles and the employer directory.")
    return " ".join(parts)


def _summary(understood: Understood, vacancy_count: int, employer_count: int, with_link: int, newest: datetime | None) -> str:
    if understood.prompt:
        return "Ask about a role, an employer, or a country. The answer uses the directory and the roles already stored."
    if not understood.supported:
        topic = ", ".join(understood.declined) or "that"
        return f"Not enough data. Sospana Sonke does not have {topic}. This search did not guess an answer."
    sentences: list[str] = []
    if understood.looking_for != "employers":
        if vacancy_count == 0:
            sentences.append("No open role in the store matches this question.")
        else:
            word = "role" if vacancy_count == 1 else "roles"
            sentences.append(f"{vacancy_count:,} open {word} in the store match.")
            if newest is not None:
                seen = newest.date().isoformat()
                sentences.append(f"The most recently seen match was last seen on the employer site on {seen}.")
    if understood.looking_for == "roles" and employer_count and vacancy_count:
        word = "employer" if employer_count == 1 else "employers"
        sentences.append(f"Those roles are at {employer_count:,} {word}.")
    if understood.looking_for != "roles":
        if employer_count == 0:
            sentences.append("No employer in the directory matches this question.")
        elif understood.careers_link_only:
            word = "employer" if employer_count == 1 else "employers"
            verb = "has" if employer_count == 1 else "have"
            sentences.append(f"{employer_count:,} {word} in the directory {verb} a careers link stored.")
        else:
            word = "employer" if employer_count == 1 else "employers"
            verb = "has" if with_link == 1 else "have"
            sentences.append(
                f"{employer_count:,} {word} in the directory match. {with_link:,} of them {verb} a careers link stored."
            )
    if vacancy_count == 0 and (understood.looking_for == "roles" or employer_count == 0):
        sentences.append("Not enough data to answer this from the directory or the stored roles.")
    if understood.declined:
        other = [label for label in understood.declined if label != "an unemployment rate"]
        if "an unemployment rate" in understood.declined:
            sentences.append(
                "This does not include an unemployment rate. Those official rates are a separate table "
                "and are not mixed into this job count."
            )
        if other:
            sentences.append(
                "This does not include " + ", ".join(other) + ". That dataset is not in Sospana Sonke."
            )
    return " ".join(sentences)


def _limitations(understood: Understood) -> list[str]:
    limits = list(_BASE_LIMITS)
    if understood.province:
        limits.append("A province filter uses the province saved on the role. Roles with a blank province are left out.")
    if understood.city:
        limits.append("A city filter matches the location text we stored. Roles with a blank location are left out.")
    if not understood.supported and understood.declined:
        limits.append("No number was estimated for the missing dataset.")
    return limits


def _phrase(understood: Understood) -> str:
    parts: list[str] = []
    if understood.keywords:
        parts.append(understood.keywords)
    if understood.employment_type and (not understood.keywords or understood.employment_type not in understood.keywords.split()):
        parts.append(understood.employment_type)
    if understood.work_mode:
        parts.append(understood.work_mode)
    if understood.looking_for == "employers":
        parts.append(understood.source_label or "employers")
    else:
        parts.append("jobs")
        if understood.source_label:
            parts.append(understood.source_label)
    if understood.employer:
        parts.append(f"at {understood.employer}")
    if understood.city:
        parts.append(f"in {understood.city}")
    if understood.province:
        parts.append(f"in {understood.province}")
    if understood.country:
        parts.append(f"in {understood.country}")
    if understood.careers_link_only:
        parts.append("with a careers link")
    if understood.max_age_days:
        parts.append(f"in the last {understood.max_age_days} days")
    return " ".join(parts)


def _same_filters(a: Understood, b: Understood) -> bool:
    return (
        a.keywords == b.keywords
        and a.country == b.country
        and a.province == b.province
        and a.city == b.city
        and (a.employer or "").lower() == (b.employer or "").lower()
        and a.source_label == b.source_label
        and a.employment_type == b.employment_type
        and a.work_mode == b.work_mode
        and a.max_age_days == b.max_age_days
        and a.careers_link_only == b.careers_link_only
        and a.looking_for == b.looking_for
    )


def _follow_ups(db: Session, understood: Understood, names: list[str], vacancy_count: int) -> list[str]:
    if not understood.supported or understood.looking_for == "employers" or vacancy_count <= 0:
        return []
    found: list[str] = []

    def offer(candidate: Understood) -> None:
        if len(found) >= 2:
            return
        phrase = _phrase(candidate)
        parsed = parse_question(phrase, names)
        if not _same_filters(candidate, parsed):
            return
        count = _vacancy_query(db, candidate).with_entities(func.count(Vacancy.id)).scalar() or 0
        if 0 < int(count) < vacancy_count:
            found.append(phrase)

    if understood.max_age_days is None:
        offer(replace(understood, max_age_days=7))
    if understood.country == "South Africa" and not understood.province and not understood.city:
        offer(replace(understood, province="Gauteng"))
    if not understood.country:
        offer(replace(understood, country="South Africa"))
    return found


_LABOUR_STOP = frozenset({
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "me", "my",
    "show", "what", "which", "is", "are", "there", "any", "please", "how", "many",
    "does", "do", "rate", "rates", "official", "labour", "labor", "force", "survey",
    "qlfs", "stats", "statssa", "statistics", "province", "provinces", "latest",
    "current", "percent", "percentage", "level", "levels", "figure", "figures",
    "people", "high", "south", "africa", "sa", "unemployment", "unemployed",
    "email", "e-mail", "mail", "call", "phone", "contact", "number", "name",
    "expanded", "combined", "potential", "underutilisation", "underutilization",
    "lu1", "lu3", "by", "from", "between", "versus", "vs", "national", "country",
    "provincial", "table", "was", "were", "during", "quarter", "latest",
})
_JOB_TOPIC = re.compile(
    r"\b(jobs?|roles?|vacancies|vacancy|openings?|employers?|companies|hiring|"
    r"internships?|learnerships?|bursar(?:y|ies)|scholarships?|nurses?|nursing)\b",
    re.IGNORECASE,
)
_EXPANDED = re.compile(
    r"\b(expanded|combined|lu3|potential labour|potential labor|underutilis\w*|underutiliz\w*)\b",
    re.IGNORECASE,
)


def _labour_limitations(table: dict) -> list[str]:
    return [
        "These figures are copied from Statistics South Africa. Sospana Sonke did not re-estimate them.",
        "This presentation is Sospana Sonke's own application of the published table. It is not a Statistics South Africa publication.",
        table["official_definition"],
        table["expanded_definition"],
        "A difference between quarters is not an explanation of why the rate changed.",
        table["coverage"],
        table["history_note"],
        "Sampling variability is in the statistical release and is not reprinted here.",
        "This is not a count of vacancies stored by Sospana Sonke.",
        "A downloadable file is not offered. The notice permits this free display when the source is named, and it forbids selling the data.",
    ]


def _citation(table: dict, row: dict, series: str) -> dict:
    points = []
    for period, official, expanded in zip(table["periods"], row["official"], row["expanded"]):
        points.append({
            "period": period["quarter"],
            "label": period["label"],
            "rate": official if series == "official" else expanded,
        })
    return {
        "publisher": table["publisher"],
        "title": table["title"],
        "url": table["release_url"],
        "licence_url": table["licence_url"],
        "release_date": table["release_date"],
        "table": table["table"],
        "place": row["place"],
        "series": series,
        "points": points,
    }


def _labour_reply(question: str, country_names: list[str]) -> IntelligenceAnswer | None:
    """Answer a labour-rate question from the stored table, or None when it is a job question."""
    raw = " ".join((question or "").strip().split())[:200]
    if not raw or not re.search(r"\bunemploy", raw, flags=re.IGNORECASE):
        return None
    if _JOB_TOPIC.search(raw):
        return None
    lowered = raw.lower().replace("'s", " ").replace("’s", " ")
    lowered = re.sub(r"[?!,;:]+", " ", lowered)
    lowered = " ".join(lowered.split())
    for phrase, _label in _DECLINED:
        if phrase.startswith("unemployment"):
            continue
        if _contained(lowered, phrase):
            return None

    counted_at = datetime.now(timezone.utc)
    table = load_table()
    bare = Understood(supported=False, declined=("an unemployment rate",), looking_for="both")

    def refuse(summary: str, *, province: str | None = None, country: str | None = None) -> IntelligenceAnswer:
        understood = replace(bare, province=province, country=country)
        limitations = [
            "No number was estimated for a place or a group the stored table does not print.",
        ]
        reading = "The stored labour table is Statistics South Africa Table E, for South Africa and its nine provinces."
        dataset_id = None
        if table is not None:
            limitations = _labour_limitations(table) + limitations
            dataset_id = table["id"]
            reading = (
                f"The stored table is {table['table']} in {table['title']} "
                f"({table['release_url']}). It does not contain the figure this question asked for."
            )
        return IntelligenceAnswer(
            question=raw,
            understood=understood,
            enough_data=False,
            summary=summary,
            reading=reading,
            limitations=limitations,
            counted_at=counted_at,
            dataset_id=dataset_id,
            citation=None,
        )

    if table is None:
        return refuse("Not enough data. The labour table is not loaded. This search did not guess a rate.")

    text = lowered
    city = None
    for phrase in sorted(_CITY_TO_PROVINCE, key=len, reverse=True):
        if _contained(text, phrase):
            city = phrase
            text = _cut(text, phrase)
            break
    if city:
        return refuse(
            f"Not enough data. The stored table has no rate for {city.title()}. "
            "It prints the nine provinces and South Africa, and this search did not substitute a province."
        )

    other_country = None
    for phrase, canon in _country_phrases(country_names):
        if canon == "South Africa":
            continue
        if _contained(text, phrase):
            other_country = canon
            break
    if other_country:
        return refuse(
            f"Not enough data. The stored table covers South Africa, not {other_country}. "
            "This search did not guess a rate.",
            country=other_country,
        )

    province = None
    for phrase, canon in sorted(_PROVINCE_ALIASES, key=lambda item: len(item[0]), reverse=True):
        if _contained(text, phrase):
            province = canon
            text = _cut(text, phrase)
            break
    for phrase in ("south africa", "south african"):
        if _contained(text, phrase):
            text = _cut(text, phrase)

    leftover = [
        word for word in text.split()
        if "@" not in word and word.isalpha() and word not in _LABOUR_STOP and len(word) > 2
    ]
    if leftover:
        shown = " ".join(leftover[:4])
        return refuse(
            f"Not enough data. The stored table is the official rate for people aged 15 to 64. "
            f"It does not print a separate rate for {shown}. This search did not guess one."
        )

    place = province or "South Africa"
    row = place_row(place)
    if row is None:
        return refuse("Not enough data. That place is not in the stored table. This search did not guess a rate.")

    series = "expanded" if _EXPANDED.search(raw) else "official"
    series_name = (
        "combined rate of unemployment and the potential labour force"
        if series == "expanded"
        else "official unemployment rate"
    )
    current = latest_rate(row, series)
    latest = table["periods"][-1]
    earlier = []
    for period, value in zip(table["periods"][:-1], row[series][:-1]):
        earlier.append(f"{value}% in {period['label']}")
    history = ""
    if earlier:
        history = " In the same table it was " + " and ".join(earlier) + "."
    where = "South Africa" if place == "South Africa" else place
    summary = (
        f"In {where}, the {series_name} was {current}% in {latest['label']} "
        f"({latest['quarter']}).{history} "
        f"Source: {table['publisher']}, {table['title']}, {table['table']}, "
        f"released {table['release_date']}."
    )
    understood = Understood(
        country="South Africa",
        province=province,
        looking_for="both",
        supported=True,
    )
    return IntelligenceAnswer(
        question=raw,
        understood=understood,
        enough_data=True,
        summary=summary,
        reading=(
            "The figure is the one printed for that place. "
            "Open the statistical release for the sampling error and the full definitions."
        ),
        limitations=_labour_limitations(table),
        counted_at=counted_at,
        dataset_id=table["id"],
        citation=_citation(table, row, series),
    )


def answer_question(db: Session, question: str) -> IntelligenceAnswer:
    names = load_country_names(db)
    labour = _labour_reply(question, names)
    if labour is not None:
        return labour
    understood = parse_question(question, names)
    counted_at = datetime.now(timezone.utc)
    if understood.prompt or not understood.supported:
        return IntelligenceAnswer(
            question=" ".join((question or "").strip().split())[:200],
            understood=understood,
            enough_data=False,
            summary=_summary(understood, 0, 0, 0, None),
            reading=_reading(understood),
            limitations=_limitations(understood),
            counted_at=counted_at,
        )

    vacancy_count = 0
    vacancies: list[dict] = []
    newest: datetime | None = None
    employer_rows: list[Company] = []
    employer_count = 0
    with_link = 0

    if understood.looking_for != "employers":
        vq = _vacancy_query(db, understood)
        vacancy_count = int(vq.with_entities(func.count(Vacancy.id)).scalar() or 0)
        employer_count = int(vq.with_entities(func.count(func.distinct(Company.id))).scalar() or 0)
        with_link = int(
            vq.filter(Company.careers_url.isnot(None), Company.careers_url != "")
            .with_entities(func.count(func.distinct(Company.id)))
            .scalar()
            or 0
        )
        rows = vq.order_by(Vacancy.last_seen_at.desc()).limit(40).all()
        seen: set[str] = set()
        for vacancy, company in rows:
            if len(vacancies) < SAMPLE:
                vacancies.append(_public_vacancy(vacancy, company))
                if newest is None:
                    newest = vacancy.last_seen_at
            if company.id not in seen and len(employer_rows) < SAMPLE:
                employer_rows.append(company)
                seen.add(company.id)
    else:
        eq = _employer_query(db, understood)
        employer_count = int(eq.order_by(None).count())
        if understood.careers_link_only:
            with_link = employer_count
        else:
            with_link = int(
                _employer_query(db, understood)
                .filter(Company.careers_url.isnot(None), Company.careers_url != "")
                .order_by(None)
                .count()
            )
        employer_rows = (
            eq.order_by(
                case(
                    (and_(Company.careers_url.isnot(None), Company.careers_url != ""), 0),
                    else_=1,
                ),
                Company.company_name,
            )
            .limit(SAMPLE)
            .all()
        )
        vq = _vacancy_query(db, understood)
        vacancy_count = int(vq.with_entities(func.count(Vacancy.id)).scalar() or 0)
        for vacancy, company in vq.order_by(Vacancy.last_seen_at.desc()).limit(SAMPLE).all():
            vacancies.append(_public_vacancy(vacancy, company))
            if newest is None:
                newest = vacancy.last_seen_at

    ids = [company.id for company in employer_rows]
    counts = open_vacancy_counts(db, ids)
    known = companies_with_known_vacancy_count(db, ids)
    employers = [_public_employer(company, counts, known) for company in employer_rows]

    if understood.looking_for == "roles":
        enough = vacancy_count > 0
    elif understood.looking_for == "employers":
        enough = employer_count > 0
    else:
        enough = vacancy_count > 0 or employer_count > 0

    return IntelligenceAnswer(
        question=" ".join(question.strip().split())[:200],
        understood=understood,
        enough_data=enough,
        summary=_summary(understood, vacancy_count, employer_count, with_link, newest),
        reading=_reading(understood),
        limitations=_limitations(understood),
        follow_ups=_follow_ups(db, understood, names, vacancy_count),
        vacancies=vacancies,
        vacancy_count=vacancy_count,
        employers=employers,
        employer_count=employer_count,
        with_link_count=with_link,
        counted_at=counted_at,
    )
