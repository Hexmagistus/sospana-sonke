"""Careers landing pages for large groups and listed companies."""
from app.services.seed_landing import (
    WikiEmployer,
    choose_entity,
    clean_stored_url,
    common_career_urls,
    extract_careers_links,
    labels_close,
    landing_eligible,
    language_homes,
    needs_listing_proof,
    ordered_candidates,
    page_is_careers,
    parse_wikidata_entity,
    registrable_domain,
    url_belongs_to_employer,
)


def _entity(**kwargs) -> WikiEmployer:
    base = dict(
        qid="Q1",
        label="",
        description="",
        website="",
        instance_of=frozenset(),
        exchanges=frozenset(),
        country_qids=frozenset(),
        tickers=(),
    )
    base.update(kwargs)
    return WikiEmployer(**base)


def test_landing_page_needs_no_job_list_in_the_html():
    assert page_is_careers("https://www.sap.com/about/careers.html", "<html></html>")
    assert page_is_careers("https://careers.adidas-group.com/", "")
    assert page_is_careers("https://www.example.com/en", "<title>Careers at Eni</title>")
    assert page_is_careers("https://www.example.com/about", "<h1>Karriere</h1>")
    assert page_is_careers("https://www.marubeni.com/jp/recruit/", "<title>採用情報</title>")
    assert not page_is_careers("https://www.adidas.com/", "<title>adidas</title><h1>Home</h1>")
    assert not page_is_careers("https://www.linkedin.com/company/adidas/jobs", "<title>Jobs</title>")
    assert not page_is_careers("https://www.example.com/news/jobs-roundup", "<title>Jobs roundup</title>")
    assert not page_is_careers("https://www.airarabia.com/en/not-found", "<title>Careers</title>")
    assert "utm_source" not in clean_stored_url(
        "https://saputo.wd5.myworkdayjobs.com/en-US/Saputo?locationCountry=abc&amp;utm_source=saputo-com"
    )
    assert "locationCountry=abc" in clean_stored_url(
        "https://saputo.wd5.myworkdayjobs.com/en-US/Saputo?locationCountry=abc&amp;utm_source=saputo-com"
    )


def test_own_domain_and_sibling_careers_host():
    assert registrable_domain("careers.adidas-group.com") == "adidas-group.com"
    assert registrable_domain("www.sap.com") == "sap.com"
    assert registrable_domain("jobs.co.za") == "jobs.co.za"
    official = "https://www.adidas.com/"
    assert url_belongs_to_employer("Adidas", official, "https://www.adidas.com/careers", linked_from_homepage=False)
    assert url_belongs_to_employer(
        "Adidas", official, "https://careers.adidas-group.com/", linked_from_homepage=True,
    )
    assert not url_belongs_to_employer(
        "Adidas", official, "https://careers.adidas-group.com/", linked_from_homepage=False,
    )
    assert not url_belongs_to_employer(
        "Adidas", official, "https://www.linkedin.com/jobs", linked_from_homepage=True,
    )
    assert not url_belongs_to_employer(
        "Arch Capital Group", official, "https://jobs.ashbyhq.com/arch", linked_from_homepage=True,
    )


def test_eligibility_includes_listed_africa_and_excludes_local_companies():
    assert landing_eligible("PRIVATE", "2026-10-11 europe-employers: DAX. No board.")
    assert landing_eligible("JSE", "")
    assert landing_eligible("EGX", "BRICS partner: no direct careers page")
    assert landing_eligible("SOE", "EGX-listed state-linked tobacco monopoly")
    assert landing_eligible("NSE", "BRICS partner: listed by name only")
    assert not landing_eligible("PRIVATE", "Food chain; not JSE-listed.")
    assert not landing_eligible("PRIVATE", "2026-10-11 mena-employers: companies. No board.")
    assert not landing_eligible("PRIVATE", "2026-10-11 uk-employers: AIM. No board.")
    assert not landing_eligible("UNI", "2026-10-11 europe-employers: universities.")
    assert needs_listing_proof("PRIVATE", "2026-10-11 africa-employers: companies.", "Morocco")
    assert needs_listing_proof("PRIVATE", "2026-10-11 mena-employers: companies.", "Saudi Arabia")
    assert not needs_listing_proof("PRIVATE", "2026-10-11 mena-employers: Dubai Financial Market.", "United Arab Emirates")
    assert not needs_listing_proof("PRIVATE", "2026-10-11 africa-employers: companies.", "Ghana")


def test_wikidata_item_must_be_the_company_not_a_city_or_person():
    adidas = _entity(
        qid="Q3895", label="Adidas AG", description="German multinational corporation",
        website="https://www.adidas.com/", instance_of=frozenset({"Q4830453", "Q891723"}),
        country_qids=frozenset({"Q183"}),
    )
    city = _entity(
        qid="Q64", label="Berlin", description="capital of Germany",
        website="https://www.berlin.de/", instance_of=frozenset({"Q515"}),
        country_qids=frozenset({"Q183"}),
    )
    person = _entity(
        qid="Q1", label="Eni", description="male given name",
        website="https://example.com/", instance_of=frozenset({"Q5"}),
    )
    assert labels_close("Adidas", "Adidas AG")
    assert labels_close("Saputo Inc.", "Saputo")
    assert labels_close("Hermès", "Hermes")
    assert not labels_close("Bidcorp", "Bidcorp Foodservice (Europe)")
    assert choose_entity("Adidas", "Germany", [adidas, city], require_listing=False) == adidas
    assert choose_entity("Berlin", "Germany", [city], require_listing=False) is None
    assert choose_entity("Eni", "Italy", [person], require_listing=False) is None
    listed = _entity(
        qid="Q9", label="Almarai", description="Saudi dairy company",
        website="https://www.almarai.com/", instance_of=frozenset({"Q783794"}),
        exchanges=frozenset({"Q2006583"}), country_qids=frozenset({"Q851"}),
    )
    private = _entity(
        qid="Q8", label="Al Baik", description="Saudi restaurant chain",
        website="https://www.albaik.com/", instance_of=frozenset({"Q783794"}),
        country_qids=frozenset({"Q851"}),
    )
    assert choose_entity("Almarai", "Saudi Arabia", [listed, private], require_listing=True) == listed
    assert choose_entity("Al Baik", "Saudi Arabia", [private], require_listing=True) is None


def test_parse_entity_and_candidate_order():
    raw = {
        "labels": {"en": {"value": "Adidas AG"}},
        "descriptions": {"en": {"value": "German multinational corporation"}},
        "claims": {
            "P856": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": "https://www.adidas.com/"}}}],
            "P31": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q4830453"}}}}],
            "P17": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q183"}}}}],
        },
    }
    parsed = parse_wikidata_entity("Q3895", raw)
    assert parsed.website == "https://www.adidas.com/"
    assert "Q4830453" in parsed.instance_of
    html = """
    <a href="/products">Shop</a>
    <a href="https://careers.adidas-group.com/">Careers</a>
    <a href="https://www.linkedin.com/company/adidas/jobs">LinkedIn jobs</a>
    """
    links = extract_careers_links(html, "https://www.adidas.com/")
    assert links == ["https://careers.adidas-group.com/"]
    ordered = ordered_candidates("Adidas", "Germany", "https://www.adidas.com/", links)
    assert ordered[0] == "https://careers.adidas-group.com/"
    kering = ordered_candidates(
        "Kering", "France", "https://www.kering.com/en/",
        ["https://www.kering.com/en/talent/job-offers/"], ["/fr/"],
    )
    assert kering[0] == "https://www.kering.com/en/talent/job-offers/"
    assert any(url.endswith("/karriere") for url in common_career_urls("https://www.sap.com/"))
    assert "https://careers.sap.com/" in common_career_urls("https://www.sap.com/")
    homes = language_homes('<a href="/jp/">日本語</a><a href="/en/careers">Careers</a>', "https://www.marubeni.com/en/")
    assert homes == ["https://www.marubeni.com/jp/"]
    prefixed = common_career_urls("https://www.marubeni.com/en/", ["/jp/"])
    assert "https://www.marubeni.com/jp/recruit" in prefixed
