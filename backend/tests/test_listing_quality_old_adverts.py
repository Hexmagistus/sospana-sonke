"""Old adverts whose year or date sits in the title or in the link's file name."""
from datetime import date, datetime, timedelta, timezone

from app.models.company import Company
from app.models.vacancy import Vacancy, VacancySource
from app.services.listing_quality import (
    apply_listing_quality,
    old_advert_reasons,
    removal_reasons,
    stamp_text_failures,
    text_names_passed_date,
)
from app.services.opportunity_expiry import is_publicly_listed

TODAY = date(2026, 10, 18)


def _reasons(title, url=None):
    return removal_reasons(
        title=title, description=None, posting_date=None, closing_date=None,
        application_url=url, today=TODAY,
    )


def test_programme_check_examples_are_caught():
    cases = [
        ("Updated Advert for Various Learnerships :Closing 28 August 2026",
         "https://www.mopani.gov.za/docs/Updated Advert for Various Learnerships.pdf"),
        ("learnership-Food and Beverage Handling Processes",
         "https://www.vhembecollege.edu.za/wp-content/uploads/2021/03/learnership-Food-and-Beverage-Handling-Processes.pdf"),
        ("ELETRONICS NQF LEVEL 3 LEARNERSHIP",
         "https://www.vhembecollege.edu.za/wp-content/uploads/2020/09/ELETRONICS-NQF-LEVEL-3-LEARNERSHIP.pdf"),
        ("Bursary opportunities", "https://pepkor.co.za/wp-content/uploads/PLR_CA_2022-bursary-ad.pdf"),
        ("ADVERTISEMENT OF HEALTH AND SAFETY LEARNERSHIP",
         "https://www.tswelopele.gov.za/wp-content/uploads/2025/06/ADVERTISEMENT-OF-HEALTH-AND-SAFETY-LEARNERSHIP.pdf"),
        ("Learnership Opportunities for Learner Traffic Officers",
         "https://www.limpopo.gov.za/wp-content/uploads/2023/06/Traffic-Officers-Learnership.pdf"),
        ("Bursary Form", "http://www.mkhondo.gov.za/wp-content/uploads/2025/01/BURSARY-APPLICATION-FORM-2025-1.pdf"),
        ("Drivers | Closing: 25 October 2018", "https://www.mopani.gov.za/docs/vacancies/Monapni17102018.pdf"),
        ("Trainee Traffic Officer 05 August 2005", None),
        ("Traffic Officers - Speed Violations X3",
         "https://www.knysna.gov.za/wp-content/uploads/2026/04/Traffic-Officers-speed-violations_Apr-2026.pdf"),
        ("Traffic Officer Post",
         "https://www.dikgatlong.gov.za/notices/vacancies?download=180:traffic-officer-x2-closing-date-06-september-2024"),
    ]
    for title, url in cases:
        assert _reasons(title, url), title


def test_current_adverts_stay():
    keep = [
        ("Traffic Officers - Speed Violations X3",
         "https://www.knysna.gov.za/wp-content/uploads/2026/09/Traffic-Officers-speed-violations_Sept-2026.pdf"),
        ("Bursary Awards 2027", "https://www.nda.gov.za/images/Vacancies/bursaries/2027-doa-bursary-awards-advert.pdf"),
        ("Project Manager", "https://careers.cityofsydney.nsw.gov.au/job/Sydney-Project-Manager-NSW-2000/1368720366/"),
        ("Senior Product Development Engineer",
         "https://careers.fphcare.com/job/East-Tamaki-Senior-Product-Development-Engineer-2013/1368496666/"),
        ("Account Assistant",
         "https://mcgill.wd3.myworkdayjobs.com/en-US/McGill/job/McGill-College-2001/Account-Assistant-C_JR0000082104"),
        ("Backend Engineer", "https://jobs.lever.co/acme/6119b0aa-2017-4cf2-9346-e0e763bf71e3"),
        ("Quality Auditor ISO 9001:2015", "https://ward.example/jobs/42"),
        ("Graduate Programme closing 30 November 2026", None),
        ("Intake starts September 2026", None),
        ("THW Client Co-op (January 2027 - Rochester, NY)",
         "https://x.wd1.myworkdayjobs.com/careers/job/New-York/THW-Client-Co-op--January-2026-_R031672"),
    ]
    for title, url in keep:
        assert _reasons(title, url) == [], title


def test_passed_dates():
    assert text_names_passed_date("Closing 17 October 2026", TODAY)
    assert not text_names_passed_date("Closing 18 October 2026", TODAY)
    assert text_names_passed_date("Job-adverts-Closing-date-20-June-2025.pdf", TODAY)
    assert text_names_passed_date("Vacancy 2026-08-15", TODAY)
    assert not text_names_passed_date("PT Lecturers 2027 ChemMet 14 Oct 2026", TODAY)
    assert not text_names_passed_date("City Manager - Closing date - 30Oct2026 Erratum 2026-10-12", TODAY)
    assert text_names_passed_date("ADVERT TRAINEE TRAFFIC OFFICERS AUG 2026", TODAY)
    assert not text_names_passed_date("Advert September 2026", TODAY)
    assert not text_names_passed_date("31 February 2027 typo", TODAY)
    assert old_advert_reasons("Nurse", ("https://x.example/uploads/2026/05/nurse.pdf",), TODAY) == []


def _source(db):
    company = Company(company_name="Old Advert Municipality", country="South Africa", source_type="MUNI",
                      careers_url="https://old.example/vacancies", active=True)
    db.add(company)
    db.commit()
    source = VacancySource(company_id=company.id, url="https://old.example/vacancies", ats_type="static", active=True)
    db.add(source)
    db.commit()
    return source


def _row(db, source, title, url, marker):
    now = datetime.now(timezone.utc)
    row = Vacancy(company_id=source.company_id, source_id=source.id, title=title, content_hash=f"h-{marker}",
                  application_url=url, is_open=True, status="active", lifecycle_status="ACTIVE",
                  first_seen_at=now, last_seen_at=now, opportunity_type="learnership")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_stamping_hides_link_year_rows_and_keeps_live_ones(client, db):
    source = _source(db)
    old = _row(db, source, "Bursary opportunities", "https://pepkor.example/wp-content/uploads/PLR_CA_2022-bursary-ad.pdf", "a")
    live = _row(db, source, "Bursary opportunities", "https://pepkor.example/careers/bursary", "b")
    assert not is_publicly_listed(old)
    counts = stamp_text_failures(db)
    assert counts["past_year"] == 1
    assert counts["hidden"] == 1
    db.expire_all()
    assert db.get(Vacancy, old.id).status == "expired"
    assert db.get(Vacancy, live.id).status == "active"
    listed = client.get("/api/v1/jobs", params={"q": "Bursary"}).json()
    assert [job["id"] for job in listed["jobs"]] == [live.id]
    assert client.get(f"/api/v1/jobs/{old.id}").status_code in (404, 410)


def test_manual_close_survives_a_rescan(db):
    source = _source(db)
    row = _row(db, source, "SAICA Trainee Programme", "https://absa.example/programmes/saica", "m")
    row.quality_flags = ["manual_close"]
    row.is_open = False
    row.status = "expired"
    row.lifecycle_status = "REMOVED"
    db.commit()
    from app.services.opportunity_expiry import mark_active
    mark_active(row)
    apply_listing_quality(row)
    assert row.status == "expired"
    assert "manual_close" in row.quality_flags
    assert not is_publicly_listed(row)


def test_published_dates_are_not_closing_dates():
    assert not text_names_passed_date("IT and software development Published: 2026-10-08", TODAY)
    assert not text_names_passed_date("Engineer - Date posted: 01 October 2026", TODAY)
    assert text_names_passed_date("Warehouse Supervisor - Expiry Date: 2026-10-14", TODAY)
