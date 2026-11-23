from app.html_licence import licence_links
from app.licence import candidate_from_item, discover_items, licence_kind
from app.robots import robots_allows


def test_public_domain_and_cc_by_are_accepted():
    assert licence_kind("https://creativecommons.org/publicdomain/mark/1.0/") == "public-domain"
    assert licence_kind("http://creativecommons.org/licenses/publicdomain/") == "public-domain"
    assert licence_kind("https://creativecommons.org/publicdomain/zero/1.0/") == "cc0"
    assert licence_kind("https://creativecommons.org/licenses/by/3.0/") == "cc-by"
    assert licence_kind("https://creativecommons.org/licenses/by-sa/4.0/") == "cc-by-sa"


def test_nc_and_nd_and_missing_are_refused():
    assert licence_kind("https://creativecommons.org/licenses/by-nc-sa/4.0/") is None
    assert licence_kind("https://creativecommons.org/licenses/by-nd/4.0/") is None
    assert licence_kind("https://creativecommons.org/licenses/by-nc/4.0/") is None
    assert licence_kind("") is None
    assert licence_kind(None) is None
    assert licence_kind("not a url") is None


def test_candidate_has_an_embed_only_when_the_licence_passes():
    ok = candidate_from_item(
        {
            "identifier": "BigBuckBunny",
            "title": "Big Buck Bunny",
            "licenseurl": "https://creativecommons.org/licenses/by/3.0/",
        }
    )
    assert ok is not None
    assert ok["authorizedEmbedUrl"] == "https://archive.org/embed/BigBuckBunny"
    assert ok["rightsVerified"] is True
    refused = discover_items(
        [
            {"identifier": "x", "title": "Nope", "licenseurl": "https://creativecommons.org/licenses/by-nc/4.0/"},
            {"identifier": "y", "title": "Also no"},
        ]
    )
    assert refused == []


def test_robots_and_html_helpers():
    robots = "User-agent: *\nDisallow: /private\n"
    assert robots_allows(robots, "/movies") is True
    assert robots_allows(robots, "/private/reel") is False
    links = licence_links('<a href="https://creativecommons.org/licenses/by/3.0/">CC</a>')
    assert links == ["https://creativecommons.org/licenses/by/3.0/"]
