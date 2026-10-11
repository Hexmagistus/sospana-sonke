"""Where a job location sits, for offline seed checks.

The production scanner does not import this. A careers URL is stored only when
enough of the board's located roles are in the employer's country, or when a
stable country filter on that same board lists roles there.
"""
from __future__ import annotations

import re

# Two-letter state abbreviations are matched only after a comma, so the English
# word "in" is not read as Indiana.
_US_ABBREV = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
    "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
_US_STATES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming", "district of columbia",
    "puerto rico",
)
_US_CITIES = (
    "new york", "nyc", "brooklyn", "manhattan", "san francisco", "seattle",
    "austin", "boston", "chicago", "los angeles", "houston", "dallas", "atlanta",
    "denver", "miami", "phoenix", "philadelphia", "san diego", "san jose",
    "portland", "minneapolis", "detroit", "nashville", "charlotte", "raleigh",
    "columbus", "indianapolis", "arlington", "pittsburgh", "baltimore", "tampa",
    "orlando", "st. louis", "st louis", "cincinnati", "cleveland", "kansas city",
    "sacramento", "san antonio", "las vegas", "salt lake", "palo alto",
    "mountain view", "sunnyvale", "redmond", "bellevue", "somerville",
)
_UK_CITIES = (
    "london", "manchester", "birmingham", "leeds", "glasgow", "edinburgh",
    "bristol", "liverpool", "sheffield", "cardiff", "belfast", "newcastle",
    "nottingham", "leicester", "southampton", "reading", "brighton", "aberdeen",
    "dundee", "coventry", "york", "bath", "exeter", "norwich", "plymouth",
    "swindon", "slough", "guildford", "swansea", "inverness", "milton keynes",
    "salford", "wolverhampton", "oxford", "cambridge",
)
_CITIES = {
    "Germany": ("berlin", "munich", "münchen", "frankfurt", "hamburg", "cologne", "köln", "stuttgart", "düsseldorf", "dusseldorf", "leipzig", "dortmund", "essen", "bremen", "dresden", "hanover", "hannover", "nuremberg", "nürnberg"),
    "France": ("paris", "lyon", "marseille", "toulouse", "lille", "nantes", "strasbourg", "bordeaux", "nice"),
    "Netherlands": ("amsterdam", "rotterdam", "the hague", "den haag", "utrecht", "eindhoven"),
    "Ireland": ("dublin", "cork", "galway", "limerick"),
    "Norway": ("oslo", "bergen", "stavanger", "trondheim"),
    "Sweden": ("stockholm", "gothenburg", "goteborg", "göteborg", "malmo", "malmö"),
    "Denmark": ("copenhagen", "aarhus", "odense"),
    "Finland": ("helsinki", "espoo", "tampere"),
    "Iceland": ("reykjavik", "reykjavík"),
    "Spain": ("madrid", "barcelona", "valencia", "seville", "sevilla", "bilbao", "zaragoza"),
    "Italy": ("milan", "milano", "rome", "roma", "turin", "torino", "naples", "napoli", "florence", "firenze"),
    "Switzerland": ("zurich", "zürich", "geneva", "genève", "basel", "bern", "lausanne"),
    "Poland": ("warsaw", "warszawa", "krakow", "kraków", "cracow", "wroclaw", "wrocław", "gdansk", "gdańsk", "poznan", "poznań"),
    "Japan": ("tokyo", "osaka", "yokohama", "nagoya", "kyoto", "sapporo", "fukuoka", "kobe"),
    "South Korea": ("seoul", "busan", "incheon", "daegu", "daejeon"),
    "Canada": ("toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "edmonton", "winnipeg", "ontario", "quebec", "québec", "british columbia"),
    "United Arab Emirates": ("dubai", "abu dhabi", "sharjah"),
    "Saudi Arabia": ("riyadh", "jeddah", "dammam", "dhahran"),
    "Qatar": ("doha",),
    "Israel": ("tel aviv", "jerusalem", "haifa", "beer sheva", "beersheba"),
    "Nigeria": ("lagos", "abuja", "port harcourt", "ibadan", "kano"),
    "Kenya": ("nairobi", "mombasa", "kisumu"),
    "Egypt": ("cairo", "alexandria", "giza"),
    "Morocco": ("casablanca", "rabat", "marrakech", "marrakesh", "tangier"),
    "Ghana": ("accra", "kumasi"),
}
_OTHER_MARKERS = (
    "singapore", "india", "bengaluru", "bangalore", "hyderabad", "mumbai", "pune",
    "chennai", "sydney", "melbourne", "australia", "hong kong", "beijing",
    "shanghai", "china", "mexico", "brazil", "são paulo", "sao paulo", "auckland",
    "new zealand",     "johannesburg", "cape town", "south africa", "pretoria",
)
_BLANK = {
    "n/a", "na", "remote", "hybrid", "anywhere", "multiple locations", "various",
    "tbd", "none", "-", "worldwide", "global", "remote - emea", "emea",
}
_PHRASES = (
    ("northern ireland", "United Kingdom"),
    ("united kingdom", "United Kingdom"),
    ("great britain", "United Kingdom"),
    ("united states of america", "United States"),
    ("united states", "United States"),
    ("u.s.a.", "United States"),
    ("u.s.", "United States"),
    ("united arab emirates", "United Arab Emirates"),
    ("saudi arabia", "Saudi Arabia"),
    ("south korea", "South Korea"),
    ("north korea", "Other"),
    ("south africa", "Other"),
    ("hong kong", "Other"),
    ("new zealand", "Other"),
    ("deutschland", "Germany"),
    ("germany", "Germany"),
    ("france", "France"),
    ("netherlands", "Netherlands"),
    ("holland", "Netherlands"),
    ("ireland", "Ireland"),
    ("norway", "Norway"),
    ("sweden", "Sweden"),
    ("denmark", "Denmark"),
    ("finland", "Finland"),
    ("iceland", "Iceland"),
    ("spain", "Spain"),
    ("españa", "Spain"),
    ("italy", "Italy"),
    ("italia", "Italy"),
    ("switzerland", "Switzerland"),
    ("schweiz", "Switzerland"),
    ("poland", "Poland"),
    ("polska", "Poland"),
    ("japan", "Japan"),
    ("canada", "Canada"),
    ("qatar", "Qatar"),
    ("israel", "Israel"),
    ("nigeria", "Nigeria"),
    ("kenya", "Kenya"),
    ("egypt", "Egypt"),
    ("morocco", "Morocco"),
    ("ghana", "Ghana"),
    ("singapore", "Other"),
    ("australia", "Other"),
    ("india", "Other"),
    ("china", "Other"),
    ("brazil", "Other"),
    ("mexico", "Other"),
)


def _word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def classify_location(location: str | None) -> str | None:
    """Return a country name, ``Other``, or None when the text names no place.

    None means the role is not located (blank, or a remote label with no
    country). Those roles stay out of the in-country share.
    """
    if not location:
        return None
    padded = " " + re.sub(r"\s+", " ", location).strip().lower() + " "
    bare = padded.strip()
    if bare in _BLANK or re.fullmatch(r"remote( \([^)]+\))?", bare):
        # "Remote (United States)" still names a country; only a bare remote does not.
        if bare in _BLANK or bare == "remote":
            return None
    scan = padded
    found: set[str] = set()
    if "northern ireland" in scan:
        found.add("United Kingdom")
        scan = scan.replace("northern ireland", " ")
    for phrase, country in _PHRASES:
        if phrase == "ireland":
            if _word(scan, "ireland"):
                found.add(country)
            continue
        if phrase in scan:
            found.add(country)
    if _word(scan, "uk") or "u.k." in scan or _word(scan, "england") or _word(scan, "scotland") or _word(scan, "wales"):
        found.add("United Kingdom")
    if _word(scan, "usa") or _word(scan, "us"):
        found.add("United States")
    if _word(scan, "uae"):
        found.add("United Arab Emirates")
    if _word(scan, "korea") and "north korea" not in scan and "south korea" not in scan:
        found.add("South Korea")
    if len(found) == 1:
        return next(iter(found))
    if len(found) > 1:
        return "Other"

    hits: set[str] = set()
    state = any(_word(padded, name) for name in _US_STATES)
    abbrev = any(re.search(rf",\s*{ab.lower()}\b", padded) for ab in _US_ABBREV)
    if state or abbrev or any(_word(padded, city) for city in _US_CITIES):
        hits.add("United States")
    if any(_word(padded, city) for city in _UK_CITIES):
        hits.add("United Kingdom")
    for country, cities in _CITIES.items():
        if any(_word(padded, city) for city in cities):
            hits.add(country)
    if any(_word(padded, mark) for mark in _OTHER_MARKERS):
        hits.add("Other")
    if len(hits) == 1:
        return next(iter(hits))
    if "United States" in hits and (state or abbrev):
        # "Paris, Texas" and "Manchester, NH" are the state, not the other city.
        explicit_uk = "united kingdom" in padded or _word(padded, "england")
        if not explicit_uk:
            return "United States"
    if "Canada" in hits and any(part in padded for part in ("ontario", "british columbia", "quebec", "québec")):
        return "Canada"
    if len(hits) > 1:
        return "Other"
    return None


def tally_locations(locations: list[str], country: str) -> tuple[int, int, float]:
    """Return ``(in_country, located, share)``. Unlocated roles are left out."""
    here = located = 0
    for location in locations:
        kind = classify_location(location)
        if kind is None:
            continue
        located += 1
        if kind == country:
            here += 1
    share = (here / located) if located else 0.0
    return here, located, share
