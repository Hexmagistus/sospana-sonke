"""In-country board decisions and Workday country filters."""
from app.services.seed_board import (
    decide_board,
    decide_counts,
    names_match,
    slug_variants,
    is_large_group,
    slug_is_reliable,
    tenant_fits,
    workday_country_facet,
    workday_filter_url,
)
from app.services.seed_locations import classify_location


def test_location_labels_match_the_country_they_name():
    assert classify_location("London") == "United Kingdom"
    assert classify_location("London, Ontario") == "Canada"
    assert classify_location("London, KY") == "United States"
    assert classify_location("Singapore") == "Other"
    assert classify_location("Seattle, San Francisco, New York City") == "United States"
    assert classify_location("N/A") is None
    assert classify_location("Remote") is None
    assert classify_location("Remote - United States") == "United States"
    assert classify_location("Manchester, NH") == "United States"
    assert classify_location("Cambridge, MA") == "United States"
    assert classify_location("Oxford, England") == "United Kingdom"
    assert classify_location("Paris, Texas") == "United States"
    assert classify_location("Paris, France") == "France"
    assert classify_location("Berlin, Germany") == "Germany"
    assert classify_location("Tokyo") == "Japan"
    assert classify_location("Seoul, Korea") == "South Korea"
    assert classify_location("Dubai") == "United Arab Emirates"
    assert classify_location("Lagos") == "Nigeria"


def test_names_do_not_collapse_neighbours():
    assert names_match("University of Oxford", "Oxford")
    assert not names_match("University of Oxford", "Oxford Instruments")
    assert names_match("Goldman Sachs", "Goldman Sachs Group")
    assert "americanexpress" in {slug.replace("-", "") for slug in slug_variants("American Express")}
    assert tenant_fits("Williams-Sonoma, Inc", "williams") is False
    assert tenant_fits("Abbott Laboratories", "abbott") is True
    assert slug_is_reliable("Abbott Laboratories", "https://abbott.wd5.myworkdayjobs.com/External")
    assert slug_is_reliable("Analog Devices", "https://analogdevices.wd1.myworkdayjobs.com/External")
    assert not slug_is_reliable("Arch Capital Group", "https://jobs.ashbyhq.com/arch")
    assert not slug_is_reliable("Universal Health Services", "https://job-boards.greenhouse.io/universal")
    assert not slug_is_reliable("Charles River Laboratories", "https://job-boards.greenhouse.io/charles")
    assert not slug_is_reliable("Williams-Sonoma, Inc", "https://williams.wd5.myworkdayjobs.com/External")
    assert tenant_fits("Analog Devices", "analogdevices") is True
    assert is_large_group("PRIVATE", "2026-10-11 europe-employers: ISEQ 20. No board.")
    assert is_large_group("PRIVATE", "2026-10-11 usa-employers: S&P 500. No board.")
    assert is_large_group("HOSPITAL", "2026-10-11 usa-employers: US hospital systems. No board.")
    assert not is_large_group("PRIVATE", "2026-10-11 uk-employers: AIM. No board.")
    assert not is_large_group("UNI", "2026-10-11 europe-employers: universities. No board.")
    assert not is_large_group("HOSPITAL", "2026-10-11 uk-employers: NHS trusts. No board.")
    assert not is_large_group("PRIVATE", "2026-10-11 mena-employers: companies. No board.")
    assert slug_variants("The Group") == []


def test_majority_accepts_the_board_and_a_minority_needs_a_filter():
    us = ["Austin, TX"] * 8 + ["Berlin, Germany"] * 2
    majority = decide_board(us, "United States")
    assert majority.accept is True and majority.filtered is False
    assert majority.here == 8 and majority.located == 10

    mixed = ["Austin, TX"] * 3 + ["Berlin, Germany"] * 7
    filtered = decide_board(mixed, "United States")
    assert filtered.accept is True and filtered.filtered is True

    thin = decide_board(["Austin, TX", "Berlin, Germany"], "United States")
    assert thin.accept is False
    assert decide_counts(2, 2).filtered is False
    assert decide_counts(2, 10).filtered is True
    assert decide_counts(1, 10).accept is False


def test_workday_country_facet_builds_a_stable_filter_url():
    payload = {
        "facets": [
            {
                "facetParameter": "locationMainGroup",
                "values": [
                    {
                        "facetParameter": "locationCountry",
                        "values": [
                            {"descriptor": "Germany", "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "count": 7},
                            {"descriptor": "United States", "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "count": 3},
                        ],
                    }
                ],
            }
        ]
    }
    found = workday_country_facet(payload, "United States")
    assert found == ("locationCountry", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", 3, 10)
    url = workday_filter_url(
        "https://acme.wd5.myworkdayjobs.com/External",
        found[1],
        found[0],
    )
    assert url == (
        "https://acme.wd5.myworkdayjobs.com/External"
        "?locationCountry=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    assert workday_country_facet({"facets": []}, "United States") is None


def test_workday_location_country_facet_keeps_its_own_parameter():
    payload = {
        "facets": [
            {
                "facetParameter": "Location_Country",
                "values": [
                    {"descriptor": "Canada", "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "count": 104},
                    {"descriptor": "United Kingdom", "id": "cccccccccccccccccccccccccccccccc", "count": 8},
                ],
            }
        ]
    }
    found = workday_country_facet(payload, "United Kingdom")
    assert found == ("Location_Country", "cccccccccccccccccccccccccccccccc", 8, 112)
    url = workday_filter_url("https://aviva.wd1.myworkdayjobs.com/External", found[1], found[0])
    assert url.endswith("?Location_Country=cccccccccccccccccccccccccccccccc")
