"""Official careers landing pages for large groups and listed companies.

A landing page counts when it is the employer's own careers or jobs page,
even if the HTML lists no openings and has no country filter. The host is
the employer's own domain or its own applicant-tracking tenant. A homepage,
a LinkedIn page, or an aggregator does not count.

Used by the offline discovery script. The scan cron does not import this.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from app.services.seed_board import _fold, is_large_group, slug_is_reliable

# African exchange rows already in the seed. NSE as a source type is the
# Indian exchange code on those rows, not a Nairobi note.
AFRICAN_LISTED_TYPES = frozenset({
    "JSE", "EGX", "ZSE", "BSE", "BVM", "ESE", "NSX", "VFEX",
})

# Private companies in these countries are not on a named large-cap list.
# A landing page is stored only when Wikidata records a listing there.
LISTING_PROOF_COUNTRIES = frozenset({
    "Saudi Arabia", "Morocco", "Nigeria", "Kenya",
})

_NATIONAL_EXCHANGES = {
    "Saudi Arabia": frozenset({"Q2006583"}),  # Saudi Stock Exchange (Tadawul)
    "Morocco": frozenset({"Q2602796"}),  # Casablanca Stock Exchange
    "Nigeria": frozenset({"Q838766"}),  # Nigerian Exchange Group
    "Kenya": frozenset({"Q2384385"}),  # Nairobi Stock Exchange
    "Egypt": frozenset({"Q1577968"}),
    "South Africa": frozenset({"Q627514"}),
}

_COUNTRY_QIDS = {
    "Saudi Arabia": "Q851",
    "Morocco": "Q1028",
    "Nigeria": "Q1033",
    "Kenya": "Q114",
    "Egypt": "Q79",
    "South Africa": "Q258",
    "Germany": "Q183",
    "France": "Q142",
    "Italy": "Q38",
    "Netherlands": "Q55",
    "Japan": "Q17",
    "Canada": "Q16",
    "United States": "Q30",
    "United Kingdom": "Q145",
    "United Arab Emirates": "Q878",
    "Australia": "Q408",
    "India": "Q668",
    "South Korea": "Q884",
    "Switzerland": "Q39",
    "Spain": "Q29",
    "Sweden": "Q34",
    "Denmark": "Q35",
    "Finland": "Q33",
    "Norway": "Q20",
    "Ireland": "Q27",
    "Poland": "Q36",
    "Israel": "Q801",
    "Qatar": "Q846",
    "Brazil": "Q155",
    "Mexico": "Q96",
    "Singapore": "Q334",
    "New Zealand": "Q664",
    "Indonesia": "Q252",
    "Malaysia": "Q833",
    "Thailand": "Q869",
    "Philippines": "Q928",
    "Vietnam": "Q881",
    "Colombia": "Q739",
    "Iceland": "Q189",
    "Belgium": "Q31",
    "Austria": "Q40",
    "Portugal": "Q45",
    "China": "Q148",
    "Hong Kong": "Q8646",
    "Taiwan": "Q865",
}

# Business-like instance-of values. A city, a person, or a video game is not.
_EMPLOYER_QIDS = frozenset({
    "Q4830453",  # business
    "Q783794",  # company
    "Q891723",  # public company
    "Q6881511",  # enterprise
    "Q1341478",  # holding company? used on oil majors; kept if description agrees
    "Q46970",  # airline
    "Q22687",  # bank
    "Q1616075",  # fashion house
    "Q4830453",
    "Q891723",
    "Q43229",  # organization — only counts together with a company description
})
_REJECT_QIDS = frozenset({
    "Q515",  # city
    "Q5",  # human
    "Q6256",  # country
    "Q82794",  # geographic region
    "Q486972",  # human settlement
    "Q3957",  # town
    "Q1549591",  # big city
    "Q5119",  # capital
    "Q484170",  # commune of France
    "Q532",  # village
    "Q7889",  # video game
    "Q11424",  # film
    "Q482994",  # album
})
_BAD_DESCRIPTION = (
    "video game", "given name", "female given name", "male given name",
    "family name", "surname", "commune", "village", "football", "film",
    "song", "album", "skyscraper", "painter",
)
_LEGAL_FORMS = frozenset({
    "inc", "incorporated", "corp", "corporation", "plc", "ltd", "limited",
    "llc", "lp", "company", "co", "the", "ag", "se", "nv", "bv", "spa",
    "gmbh", "sarl", "sas", "ab", "asa", "oyj", "kk", "sa", "pjsc", "jsc",
    "ltda", "group", "holdings", "holding", "international", "intl", "and",
    "of", "for",
})
_PATH_MARKERS = (
    "career", "jobs", "job", "karriere", "carriere", "recruit", "recrut",
    "saiyo", "vacanc", "empleo", "lavora", "werken", "stellen", "offre",
    "join-us", "joinus", "work-with-us",
)
_TEXT_MARKERS = (
    "career", "careers", "jobs", "karriere", "recrutement", "recruitment",
    "recruit", "vacancies", "vacancy", "join us", "work with us", "saiyo",
    "採用", "求人", "キャリア", "وظائف",
)
_CAREERS_HOSTS = ("careers.", "career.", "jobs.", "job.", "karriere.")
_AGGREGATORS = frozenset({
    "linkedin.com", "indeed.com", "glassdoor.com", "glassdoor.co.uk",
    "ziprecruiter.com", "monster.com", "bayt.com", "pnet.co.za",
    "careers24.com", "brightermonday.com", "jobberman.com", "myjobmag.com",
    "seek.com", "seek.co.nz", "naukri.com", "reed.co.uk", "totaljobs.com",
    "simplyhired.com", "jooble.org", "talent.com", "wellfound.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "wikipedia.org", "wikidata.org",
})
_ATS_SUFFIXES = (
    "myworkdayjobs.com", "greenhouse.io", "lever.co", "ashbyhq.com",
    "smartrecruiters.com", "workable.com", "recruitee.com", "icims.com",
    "oraclecloud.com", "successfactors.com", "successfactors.eu",
    "taleo.net", "breezy.hr", "csod.com", "pinpointhq.com", "ci.hr",
)
_MULTI_PART_SUFFIX = frozenset({
    "co.uk", "com.au", "co.za", "co.jp", "com.br", "co.nz", "com.sg",
    "com.hk", "co.kr", "com.mx", "co.ke", "com.ng", "com.eg", "co.ma",
    "com.tr", "com.tw", "com.cn", "co.in", "com.sa", "com.ae", "co.il",
    "com.ar", "com.ph", "co.id", "com.my", "com.vn", "co.zw", "co.bw",
    "co.mz", "co.na", "com.br",
})
_COMMON_PATHS = (
    "/careers",
    "/jobs",
    "/karriere",
    "/carrieres",
    "/careers.html",
    "/about/careers.html",
    "/en/careers",
    "/company/careers",
    "/saiyo",
    "/recruit",
    "/join-us",
    "/work-with-us",
)
_COUNTRY_HINTS = {
    "Germany": ("/de/", "/de-de", "germany", "deutschland"),
    "France": ("/fr/", "/fr-fr", "france"),
    "Netherlands": ("/nl/", "netherlands", "nederland"),
    "Italy": ("/it/", "italia", "/italy"),
    "Spain": ("/es/", "espana", "españa"),
    "Japan": ("/jp/", "/ja/", "/japan"),
    "United Kingdom": ("/uk/", "/gb/", "united-kingdom"),
    "United States": ("/us/", "/en-us", "united-states"),
    "Canada": ("/ca/", "/en-ca", "canada"),
    "South Africa": ("/za/", "south-africa"),
    "United Arab Emirates": ("/ae/", "/uae", "united-arab-emirates"),
    "Saudi Arabia": ("/sa/", "saudi"),
    "Australia": ("/au/", "australia"),
    "India": ("/in/", "/india"),
    "South Korea": ("/kr/", "korea"),
    "Switzerland": ("/ch/", "switzerland", "schweiz"),
    "Sweden": ("/se/", "sweden", "sverige"),
    "Denmark": ("/dk/", "denmark", "danmark"),
    "Finland": ("/fi/", "finland", "suomi"),
    "Norway": ("/no/", "norway", "norge"),
    "Ireland": ("/ie/", "ireland"),
    "Poland": ("/pl/", "poland", "polska"),
    "Israel": ("/il/", "israel"),
    "Qatar": ("/qa/", "qatar"),
    "Kenya": ("/ke/", "kenya"),
    "Nigeria": ("/ng/", "nigeria"),
    "Egypt": ("/eg/", "egypt"),
    "Morocco": ("/ma/", "morocco", "maroc"),
    "Brazil": ("/br/", "brasil", "brazil"),
    "Mexico": ("/mx/", "mexico"),
}
_LISTED_NOTE = re.compile(
    r"\b(?:NGX|NSE|EGX|CSE|JSE|ZSE|BSE|NSX|VFEX|ESE|BVM)-listed\b"
    r"|Casablanca Stock Exchange",
    re.I,
)
_NOT_LISTED = re.compile(r"\bnot\s+(?:jse-)?listed\b", re.I)
_A_TAG = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_HEADING = re.compile(r"<h[12][^>]*>(.*?)</h[12]>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_CAREER_TEXT = re.compile(
    r"career|jobs?\b|karriere|carri[eè]re|recrut|saiyo|vacanc|empleo|lavora|werken|stellen|offre|emploi"
    r"|採用|求人|キャリア|募集|وظائف|التوظيف",
    re.I,
)
_SOFT_404 = ("page not found", "not found", "404", "does not exist", "no longer available")
_LANDING_TAILS = frozenset({
    "careers", "career", "jobs", "job", "karriere", "carrieres", "recruit",
    "saiyo", "job-offers", "vacancies", "vacancy", "offres",
})


@dataclass(frozen=True)
class WikiEmployer:
    qid: str
    label: str
    description: str
    website: str
    instance_of: frozenset[str]
    exchanges: frozenset[str]
    country_qids: frozenset[str]
    tickers: tuple[str, ...]


def landing_eligible(source_type: str, note: str) -> bool:
    """True when a careers landing page may be stored without an openings list.

    Large-cap notes use ``is_large_group``. African listed rows use the
    exchange source type or an explicit ``*-listed`` note. A note that says
    the employer is not listed stays on the strict rule.
    """
    text = note or ""
    if _NOT_LISTED.search(text):
        return False
    if is_large_group(source_type, text):
        return True
    if (source_type or "").strip().upper() in AFRICAN_LISTED_TYPES:
        return True
    if (source_type or "").strip().upper() == "NSE":
        return True
    return _LISTED_NOTE.search(text) is not None


def needs_listing_proof(source_type: str, note: str, country: str) -> bool:
    """National private companies that count only when Wikidata lists them."""
    if landing_eligible(source_type, note):
        return False
    if (country or "") not in LISTING_PROOF_COUNTRIES:
        return False
    return (source_type or "").strip().upper() == "PRIVATE"


def compact_name(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", _fold(name).replace("&", " and "))
    kept = [word for word in words if word not in _LEGAL_FORMS and len(word) >= 2]
    return "".join(kept)


def labels_close(seed_name: str, wiki_label: str) -> bool:
    """True when the Wikidata label is this employer, after legal suffixes."""
    left, right = compact_name(seed_name), compact_name(wiki_label)
    return len(left) >= 3 and left == right


def entity_is_employer(entity: WikiEmployer) -> bool:
    """A company or a public business. Cities, people, and games are not."""
    description = (entity.description or "").lower()
    if any(phrase in description for phrase in _BAD_DESCRIPTION):
        return False
    kinds = entity.instance_of
    if kinds & _REJECT_QIDS and not (kinds & (_EMPLOYER_QIDS - {"Q43229"})):
        return False
    business = kinds & (_EMPLOYER_QIDS - {"Q43229"})
    if business:
        return True
    if "Q43229" in kinds and any(
        word in description for word in ("company", "corporation", "business", "bank", "airline")
    ):
        return True
    if not kinds and any(
        word in description for word in ("company", "corporation", "multinational", "bank", "airline")
    ):
        return True
    return False


def is_listed_in(entity: WikiEmployer, country: str) -> bool:
    """True when Wikidata records a listing on that country's exchange."""
    wanted = _NATIONAL_EXCHANGES.get(country)
    if wanted and entity.exchanges & wanted:
        return True
    qid = _COUNTRY_QIDS.get(country)
    if entity.tickers and qid and qid in entity.country_qids:
        return True
    return False


def country_matches(entity: WikiEmployer, country: str) -> bool | None:
    """True, False, or None when Wikidata has no country."""
    qid = _COUNTRY_QIDS.get(country)
    if not entity.country_qids or not qid:
        return None
    return qid in entity.country_qids


# Country-code domains. Generic suffixes such as .com and .co are not a country.
_CCTLD_COUNTRY = {
    "za": "South Africa", "uk": "United Kingdom", "gb": "United Kingdom",
    "bw": "Botswana", "zw": "Zimbabwe", "na": "Namibia", "mz": "Mozambique",
    "ke": "Kenya", "ng": "Nigeria", "eg": "Egypt", "ma": "Morocco", "gh": "Ghana",
    "ch": "Switzerland", "de": "Germany", "fr": "France", "jp": "Japan",
    "au": "Australia", "nz": "New Zealand", "ca": "Canada", "in": "India",
    "br": "Brazil", "sa": "Saudi Arabia", "ae": "United Arab Emirates",
    "kr": "South Korea", "nl": "Netherlands", "it": "Italy", "es": "Spain",
    "se": "Sweden", "no": "Norway", "dk": "Denmark", "fi": "Finland",
    "ie": "Ireland", "il": "Israel", "be": "Belgium", "at": "Austria",
    "pl": "Poland", "sg": "Singapore", "my": "Malaysia", "id": "Indonesia",
    "th": "Thailand", "mx": "Mexico", "ar": "Argentina", "cl": "Chile",
    "mu": "Mauritius", "sz": "Eswatini", "ls": "Lesotho",
}


def website_country(url: str) -> str | None:
    """The country implied by a country-code domain, if the suffix is one."""
    domain = registrable_domain(hostname(url))
    parts = [part for part in domain.split(".") if part]
    if len(parts) < 2:
        return None
    if parts[-1] in {"com", "org", "net", "group", "io", "co", "info", "biz"}:
        return None
    return _CCTLD_COUNTRY.get(parts[-1])


def choose_entity(
    name: str,
    country: str,
    entities: list[WikiEmployer],
    *,
    require_listing: bool,
) -> WikiEmployer | None:
    """Pick the Wikidata item that is this employer and has an official site."""
    matches = [
        entity for entity in entities
        if entity.website and labels_close(name, entity.label) and entity_is_employer(entity)
    ]
    if require_listing:
        matches = [entity for entity in matches if is_listed_in(entity, country)]
    # A .ch site with no Wikidata country is not a South African employer that
    # happens to share the name. Generic domains (.com) stay eligible.
    matches = [
        entity for entity in matches
        if website_country(entity.website) in (None, country)
    ]
    if not matches:
        return None
    agreed = [entity for entity in matches if country_matches(entity, country) is True]
    if agreed:
        return agreed[0]
    remaining = [entity for entity in matches if country_matches(entity, country) is not False]
    if len(remaining) == 1:
        return remaining[0]
    return None


def parse_wikidata_entity(qid: str, entity: dict) -> WikiEmployer | None:
    if not entity or entity.get("missing"):
        return None
    labels = entity.get("labels") or {}
    label = ((labels.get("en") or {}).get("value")) or ""
    descriptions = entity.get("descriptions") or {}
    description = ((descriptions.get("en") or {}).get("value")) or ""
    claims = entity.get("claims") or {}
    websites = _claim_strings(claims, "P856")
    website = _pick_website(websites)
    return WikiEmployer(
        qid=qid,
        label=label,
        description=description,
        website=website,
        instance_of=frozenset(_claim_ids(claims, "P31")),
        exchanges=frozenset(_claim_ids(claims, "P414")),
        country_qids=frozenset(_claim_ids(claims, "P17")),
        tickers=tuple(_claim_strings(claims, "P249")),
    )


def _claim_values(claims: dict, prop: str) -> list:
    found = []
    for claim in claims.get(prop) or []:
        snak = claim.get("mainsnak") or {}
        if snak.get("snaktype") not in (None, "value"):
            continue
        value = (snak.get("datavalue") or {}).get("value")
        if value is not None:
            found.append(value)
    return found


def _claim_ids(claims: dict, prop: str) -> list[str]:
    ident = []
    for value in _claim_values(claims, prop):
        if isinstance(value, dict) and value.get("id"):
            ident.append(value["id"])
    return ident


def _claim_strings(claims: dict, prop: str) -> list[str]:
    found = []
    for value in _claim_values(claims, prop):
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
        elif isinstance(value, dict) and (value.get("text") or "").strip():
            found.append(value["text"].strip())
    return found


def _pick_website(urls: list[str]) -> str:
    clean = [url for url in urls if url.startswith("http://") or url.startswith("https://")]
    clean = [url for url in clean if "wikipedia.org" not in url and "wikidata.org" not in url]
    https = [url for url in clean if url.startswith("https://")]
    pool = https or clean
    return pool[0] if pool else ""


def registrable_domain(host: str) -> str:
    host = (host or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = [part for part in host.split(".") if part]
    if len(parts) < 2:
        return host
    tail = ".".join(parts[-2:])
    if tail in _MULTI_PART_SUFFIX and len(parts) >= 3:
        return ".".join(parts[-3:])
    return tail


def is_aggregator(host: str) -> bool:
    domain = registrable_domain(host)
    if domain in _AGGREGATORS:
        return True
    return any(domain.endswith("." + blocked) or domain == blocked for blocked in _AGGREGATORS)


def is_ats_host(host: str) -> bool:
    host = (host or "").lower()
    return any(host == suffix or host.endswith("." + suffix) for suffix in _ATS_SUFFIXES)


def hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def clean_stored_url(url: str) -> str:
    """Drop tracking parameters and HTML escapes from a stored careers URL."""
    url = unescape(url or "").strip()
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunparse(parsed._replace(query=urlencode(query), fragment=""))


def official_site_fits(name: str, official_url: str) -> bool:
    """The Wikidata website's domain actually carries this employer's name.

    A fund whose recorded website is its manager's domain is not that fund's
    own site. ``nanoporetech.com`` still fits Oxford Nanopore.
    """
    label = registrable_domain(hostname(official_url)).split(".")[0].replace("-", "")
    if len(label) < 3:
        return False
    token = compact_name(name)
    if len(token) >= 3 and (token in label or label in token):
        return True
    words = re.findall(r"[a-z0-9]+", _fold(name))
    words = [word for word in words if word not in _LEGAL_FORMS and len(word) >= 4]
    return any(word in label for word in words)


def url_belongs_to_employer(
    name: str,
    official_url: str,
    candidate_url: str,
    *,
    linked_from_homepage: bool,
) -> bool:
    """Own domain, a sibling domain the homepage itself links, or own ATS tenant."""
    host = hostname(candidate_url)
    if not host or is_aggregator(host):
        return False
    official = hostname(official_url)
    if official and registrable_domain(host) == registrable_domain(official):
        return True
    if is_ats_host(host):
        return slug_is_reliable(name, candidate_url)
    if not linked_from_homepage:
        return False
    label = registrable_domain(host).split(".")[0].replace("-", "")
    token = compact_name(name)
    words = re.findall(r"[a-z0-9]+", _fold(name))
    words = [word for word in words if word not in _LEGAL_FORMS and len(word) >= 4]
    first = words[0] if words else ""
    if first and len(first) >= 4 and first in label:
        return True
    if token and len(token) >= 4 and (token in label or label in token) and len(label) >= 4:
        return True
    return False


def _plain(fragment: str) -> str:
    text = _TAG.sub(" ", fragment or "")
    return re.sub(r"\s+", " ", text).strip()


def is_soft_404(url: str, html: str) -> bool:
    """A 200 response that is really a missing page."""
    final = (url or "").lower()
    if "not-found" in final or final.rstrip("/").endswith("/404"):
        return True
    title = _plain(_TITLE.search(html or "").group(1) if _TITLE.search(html or "") else "")
    headings = " ".join(_plain(match) for match in _HEADING.findall(html or "")[:2])
    blob = f"{title} {headings}".lower()
    return any(phrase in blob for phrase in _SOFT_404)


def page_is_careers(url: str, html: str) -> bool:
    """Path, host, title, or heading says this is a careers or jobs page."""
    if is_soft_404(url, html):
        return False
    host = hostname(url)
    if is_aggregator(host):
        return False
    if host.startswith(_CAREERS_HOSTS):
        return True
    path = (urlparse(url).path or "").lower()
    if any(part in path for part in ("/blog", "/news", "/press", "/article", "/media", "/search/")):
        return False
    if any(part in path for part in ("career-ready", "career-advice", "careers-advice", "career-development", "career-guide")):
        return False
    if any(marker in path for marker in _PATH_MARKERS):
        return True
    title = _plain(_TITLE.search(html or "").group(1) if _TITLE.search(html or "") else "")
    headings = " ".join(_plain(match) for match in _HEADING.findall(html or "")[:4])
    blob = f"{title} {headings}".lower()
    return any(marker in blob for marker in _TEXT_MARKERS)


def country_in_url(url: str, country: str) -> bool:
    hints = _COUNTRY_HINTS.get(country) or ()
    blob = (url or "").lower()
    return any(hint in blob for hint in hints)


def extract_careers_links(html: str, base_url: str) -> list[str]:
    """Nav and footer links whose text or path is about careers."""
    found: list[str] = []
    seen: set[str] = set()
    for attrs, body in _A_TAG.findall(html or ""):
        href = _HREF.search(attrs)
        if not href:
            continue
        raw = href.group(1).strip()
        if not raw or raw.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        absolute = urljoin(base_url, raw)
        if is_aggregator(hostname(absolute)):
            continue
        text = _plain(body)
        path = (urlparse(absolute).path or "").lower()
        if not (_CAREER_TEXT.search(text) or _CAREER_TEXT.search(path) or hostname(absolute).startswith(_CAREERS_HOSTS)):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        found.append(absolute)
    return found


def language_homes(html: str, base_url: str) -> list[str]:
    """Same-site language roots linked from a homepage, such as ``/jp/``."""
    found: list[str] = []
    seen: set[str] = set()
    base_host = registrable_domain(hostname(base_url))
    for attrs, _body in _A_TAG.findall(html or ""):
        href = _HREF.search(attrs)
        if not href:
            continue
        absolute = urljoin(base_url, href.group(1).strip())
        if registrable_domain(hostname(absolute)) != base_host:
            continue
        segments = _path_segments(absolute)
        if len(segments) == 1 and re.fullmatch(r"[a-z]{2}", segments[0]):
            root = f"{urlparse(absolute).scheme}://{hostname(absolute)}/{segments[0]}/"
            if root not in seen:
                seen.add(root)
                found.append(root)
        if len(found) >= 3:
            break
    return found


def common_career_urls(official_url: str, prefixes: list[str] | None = None) -> list[str]:
    """Paths and careers/jobs subdomains on the official host."""
    parsed = urlparse(official_url)
    if not parsed.scheme or not parsed.hostname:
        return []
    origin = f"{parsed.scheme}://{parsed.hostname}"
    domain = registrable_domain(parsed.hostname)
    urls = [origin + path for path in _COMMON_PATHS]
    extra = []
    for prefix in prefixes or []:
        prefix = "/" + prefix.strip("/")
        for tail in ("/recruit", "/careers", "/jobs", "/saiyo", "/karriere", "/carrieres"):
            extra.append(origin + prefix + tail)
    urls.extend(extra)
    for prefix in ("careers", "jobs", "career", "karriere"):
        urls.append(f"https://{prefix}.{domain}/")
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _path_segments(url: str) -> list[str]:
    return [part for part in (urlparse(url).path or "").lower().split("/") if part]


def rank_candidate(url: str, country: str, *, from_homepage: bool) -> int:
    """Prefer a short careers landing page, then a country path on that site."""
    score = 0
    if country_in_url(url, country):
        score += 20
    if hostname(url).startswith(_CAREERS_HOSTS) or "recruit" in hostname(url):
        score += 24
    segments = _path_segments(url)
    path = "/" + "/".join(segments)
    if any(marker in path for marker in _PATH_MARKERS):
        score += 12
    tail = segments[-1].split(".")[0] if segments else ""
    if tail in _LANDING_TAILS:
        score += 16
    score -= max(0, len(segments) - 2) * 7
    if from_homepage:
        score += 4
    return score


def ordered_candidates(
    name: str,
    country: str,
    official_url: str,
    homepage_links: list[str],
    prefixes: list[str] | None = None,
) -> list[str]:
    """Homepage careers links and common paths, shallow landing pages first."""
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for index, url in enumerate(homepage_links):
        if not url_belongs_to_employer(name, official_url, url, linked_from_homepage=True):
            continue
        if url in seen:
            continue
        seen.add(url)
        scored.append((rank_candidate(url, country, from_homepage=True), -index, url))
    for index, url in enumerate(common_career_urls(official_url, prefixes)):
        if url in seen:
            continue
        if not url_belongs_to_employer(name, official_url, url, linked_from_homepage=False):
            continue
        seen.add(url)
        scored.append((rank_candidate(url, country, from_homepage=False), -1000 - index, url))
    # A link the homepage published is tried before a guessed path, so a
    # country prefix does not crowd out the real careers URL.
    homepage = [item for item in scored if item[1] > -1000]
    guessed = [item for item in scored if item[1] <= -1000]
    homepage.sort(reverse=True)
    guessed.sort(reverse=True)
    return [url for _score, _order, url in homepage + guessed]
