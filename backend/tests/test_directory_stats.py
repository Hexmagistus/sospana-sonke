"""Public landing-page counts: all listed rows, and the ones with a direct careers link."""
from app.models.company import Company


def _add(db, name, country, *, active=True, url="https://example.com/careers", deleted=False):
    from datetime import datetime, timezone
    db.add(Company(company_name=name, country=country, active=active, careers_url=url,
                   deleted_at=datetime.now(timezone.utc) if deleted else None))


def test_stats_include_the_direct_link_counts(client, db):
    _add(db, "SA linked", "South Africa")
    _add(db, "SA inactive", "South Africa", active=False)
    _add(db, "SA no url", "South Africa", url=None)
    _add(db, "SA blank url", "South Africa", url="")
    _add(db, "SA deleted", "South Africa", deleted=True)
    _add(db, "CA linked", "Canada")
    _add(db, "Ivory", "Ivory Coast")          # alias -> canonical spelling
    db.commit()

    r = client.get("/api/v1/companies/stats")
    assert r.status_code == 200
    assert "max-age=300" in r.headers["cache-control"]
    body = r.json()
    # existing fields are unchanged: every non-deleted row
    assert body["by_country"]["South Africa"] == 4
    assert body["employers"] == 6
    # new fields: only active rows that have a careers URL
    assert body["by_country_with_link"] == {"South Africa": 1, "Canada": 1, "Côte d'Ivoire": 1}
    assert body["with_link"] == 3
    assert body["countries_with_link"] == 3


def test_stats_are_public_and_carry_no_personal_data(client, db):
    _add(db, "Only one", "Kenya")
    db.commit()
    r = client.get("/api/v1/companies/stats")   # no Authorization header
    assert r.status_code == 200
    assert set(r.json()) == {"employers", "countries", "by_country", "with_link",
                             "countries_with_link", "by_country_with_link"}
