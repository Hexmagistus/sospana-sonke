"""Closing dates read from a vacancy page's own text. Only labelled dates count."""
from datetime import date

from app.scraper.closing_date import extract_closing_date
from app.scraper.static_html import StaticHTMLStrategy


def test_labelled_dates_in_south_african_formats():
    cases = {
        "Closing Date: 20 November 2026": date(2026, 11, 20),
        "CLOSING DATE FOR APPLICATIONS: 13 November 2026 Applications should include": date(2026, 11, 13),
        "Applications close on Friday, 4th December 2026 at 16:00": date(2026, 12, 4),
        "Closing date: 24/11/2026 Number of positions: 1": date(2026, 11, 24),
        "Date Closing: Nov 26, 2026 Job Profile": date(2026, 11, 26),
        "Deadline for applications/nominations: 15h00 SAST, 30 November 2026": date(2026, 11, 30),
        "Opening Date November 6, 2026 Closing Date November 25, 2026": date(2026, 11, 25),
        "Deadline - 2026/12/01": date(2026, 12, 1),
    }
    for text, expected in cases.items():
        assert extract_closing_date(text) == expected, text


def test_unlabelled_opening_and_impossible_dates_are_ignored():
    assert extract_closing_date("Opening date 1 November 2026") is None
    assert extract_closing_date("Posted on 5 November 2026") is None
    assert extract_closing_date("Closing date: 31 Febr 2026") is None
    assert extract_closing_date("") is None
    assert extract_closing_date(None) is None
    assert extract_closing_date("Closing date: 3 May 2019") is None  # older than the earliest year


def test_navigation_links_are_not_read_as_vacancies():
    html = (
        '<a href="/jobs/apply-bursary">apply for a bursary</a>'
        '<a href="/jobs/exec">apply for an executive position</a>'
        '<a href="/jobs/detail/123">Senior Accountant</a>'
    )
    titles = [v.title for v in StaticHTMLStrategy().parse_links(html, "https://example.org/careers")]
    assert titles == ["Senior Accountant"]
