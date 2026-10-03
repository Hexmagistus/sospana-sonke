"""The adapter is a wrapper. A strategy still does the fetch."""
from app.scraper.adapter import adapter_for
from app.scraper.base import RawVacancy


def test_adapter_validate_only_requires_a_title():
    adapter = adapter_for("greenhouse")
    assert adapter.name == "greenhouse"
    blank = adapter.validate({"title": "  "})
    assert blank == ["title"]
    assert adapter.validate({"title": "Nurse"}) == []
    raw = RawVacancy(title="Nurse", location="Lusaka")
    assert adapter.extract(raw).title == "Nurse"
    fields = adapter.normalize(
        raw, company_id="co", company_name="Clinic",
        company_country="Zambia", source_url="https://boards.greenhouse.io/clinic",
    )
    assert fields["country"] == "Zambia"
    assert fields["title"] == "Nurse"
