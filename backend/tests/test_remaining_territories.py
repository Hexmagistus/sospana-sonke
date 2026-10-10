"""Remaining zero-row territories, added 2026-10-10.

A careers URL is stored only when robots.txt allows SospanaSonkeBot (or the
host publishes no robots.txt), the response is HTTP 200, and the page names
a post or says there are no openings. Login walls, JavaScript shells, and
pages that only list professions were not stored.
"""
import csv
from pathlib import Path
from urllib.parse import urlparse

CSV = Path(__file__).resolve().parents[1] / "seed" / "company_database_import.csv"
NOTE = "2026-10-10 remaining-territories"
TERRITORIES = (
    "Mayotte", "Saint Helena", "Faroe Islands", "Gibraltar", "French Polynesia", "Guam",
    "American Samoa", "Cook Islands", "Niue", "Northern Mariana Islands", "Wallis and Futuna",
    "Bermuda", "Saint Pierre and Miquelon", "Falkland Islands", "Anguilla", "Aruba",
    "British Virgin Islands", "Caribbean Netherlands", "Cayman Islands", "Curaçao",
    "Guadeloupe", "Martinique", "Montserrat", "Saint Barthélemy", "Saint-Martin",
    "Sint Maarten", "Turks and Caicos Islands", "US Virgin Islands",
)
AGGREGATORS = (
    "linkedin.", "indeed.", "glassdoor.", "pnet.co.za", "erecruit.co",
    "careers24", "jobscall", "jobwonders", "github.io",
)
LINKS = {
    ("Électricité de Mayotte", "Mayotte"): "https://www.electricitedemayotte.com/lentreprise-edm/edm-recrute/",
    ("Centre Hospitalier de Mayotte", "Mayotte"): "https://ch-mayotte-mamoudzou.mstaff.co/offers",
    ("St Helena Government", "Saint Helena"): "https://www.sainthelena.gov.sh/st-helena/government/government-vacancies/",
    ("HM Government of Gibraltar", "Gibraltar"): "https://www.gibraltar.gov.gi/press/job-opportunities",
    ("Gibraltar Health Authority", "Gibraltar"): "https://www.gha.gi/careers/",
    ("University of Gibraltar", "Gibraltar"): "https://www.unigib.edu.gi/vacancies/",
    ("Direction des Talents et de l'Innovation", "French Polynesia"): "https://www.service-public.pf/dti/concours-ph-chpf-fiches-de-poste-2/",
    ("Centre hospitalier de la Polynésie française", "French Polynesia"): "https://www.aravihi.gov.pf/offre-de-emploi/liste-toutes-offres.aspx?facet_Entity=123&lcid=1036",
    ("Guam Power Authority", "Guam"): "https://www.guampowerauthority.com/how-do-i/find-job-openings",
    ("Guam Memorial Hospital Authority", "Guam"): "https://www.gmha.org/employment/openings/",
    ("University of Guam", "Guam"): "https://www.uog.edu/administration/administration-finance/human-resources/job-opportunities",
    ("American Samoa Government", "American Samoa"): "https://www.americansamoa.gov/jobs",
    ("National Environment Service", "Cook Islands"): "https://environment.gov.ck/resources/careers/",
    ("Government of Niue", "Niue"): "https://www.gov.nu/vacancies",
    ("Anguilla Electricity Company Limited", "Anguilla"): "https://www.anglec.com/vacancies.php",
    ("British Virgin Islands Electricity Corporation", "British Virgin Islands"): "https://bvielectricity.com/about-us/careers/",
    ("Rijksdienst Caribisch Nederland", "Caribbean Netherlands"): "https://www.rijksdienstcn.com/werken-bij-rijksdienst-caribisch-nederland/vacatures",
}
LINKED = {
    "Mayotte": 2, "Saint Helena": 1, "Faroe Islands": 0, "Gibraltar": 3, "French Polynesia": 2,
    "Guam": 3, "American Samoa": 1, "Cook Islands": 1, "Niue": 1, "Northern Mariana Islands": 0,
    "Wallis and Futuna": 0, "Bermuda": 0, "Saint Pierre and Miquelon": 0, "Falkland Islands": 0,
    "Anguilla": 1, "Aruba": 0, "British Virgin Islands": 1, "Caribbean Netherlands": 1,
    "Cayman Islands": 0, "Curaçao": 0, "Guadeloupe": 0, "Martinique": 0, "Montserrat": 0,
    "Saint Barthélemy": 0, "Saint-Martin": 0, "Sint Maarten": 0, "Turks and Caicos Islands": 0,
    "US Virgin Islands": 0,
}


def _rows():
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_remaining_territories_follow_the_direct_link_rule():
    added = [row for row in _rows() if row["relevance_note"].startswith(NOTE)]
    assert len(added) == 61
    assert {row["country"] for row in added} == set(TERRITORIES)
    linked = [row for row in added if row["careers_url"]]
    assert len(linked) == len(LINKS)
    for row in added:
        assert len(row["company_name"]) <= 255
        assert len(row["source_type"]) <= 10
        assert len(row["scraping_status"]) <= 30
        assert len(row["country"]) <= 60
        assert ":443" not in row["careers_url"]
        assert ":443" not in row["official_website"]
        assert not row["relevance_note"].startswith("2026-10-09")
        if row["careers_url"]:
            assert row["active"] == "true"
            assert row["careers_status"] == "green_verified"
            assert row["scraping_status"] == "pending"
            assert row["careers_url"].startswith("https://")
            host = urlparse(row["careers_url"]).netloc.lower()
            assert not any(bit in host for bit in AGGREGATORS)
        else:
            assert row["active"] == "false"
            assert row["careers_status"] == "grey_none_verified"
            assert row["scraping_status"] == "no_url"
            assert row["careers_url"] == ""
    assert {(row["company_name"], row["country"]): row["careers_url"] for row in linked} == LINKS
    for row in added:
        if "hospitalier universitaire" in row["company_name"].casefold():
            assert row["source_type"] == "HOSPITAL"


def test_remaining_territory_link_counts():
    counts = {country: 0 for country in TERRITORIES}
    for row in _rows():
        if row["country"] not in counts:
            continue
        if row["active"] == "true" and row["careers_url"].strip():
            counts[row["country"]] += 1
    assert counts == LINKED
