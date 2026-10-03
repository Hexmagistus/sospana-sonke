"""ATS-safe CV templates: reading order, real text, and page breaks.

Text order is checked with pypdf on every run. When poppler's pdftotext is
installed, the same PDF is checked again in layout order — that is the
reading order an applicant tracking system reconstructs from the page.
"""
from __future__ import annotations

import io
import shutil
import subprocess
import tempfile

from docx import Document
from pypdf import PdfReader

from app.documents.builder import build_tailored_cv
from app.documents.render import list_templates, render_cv_docx, render_cv_pdf, template_style

HEADINGS = [
    "Summary", "Experience", "Education", "Skills",
    "Certifications", "Languages", "Memberships", "Additional",
]

MEDIUM = {
    "full_name": "Thandi Mokoena",
    "email": "thandi.mokoena@example.com",
    "phone": "082 123 4567",
    "city": "Johannesburg",
    "country": "South Africa",
    "linkedin_url": "https://www.linkedin.com/in/thandi-mokoena",
    "summary": (
        "Operations supervisor with 6 years of experience across logistics and warehouse management. "
        "Skilled in SQL, Excel and inventory control."
    ),
    "skills": ["SQL", "Excel", "Inventory control"],
    "experience": [
        {
            "position": "Operations Supervisor",
            "employer": "Acme Logistics",
            "start_date": "2021-03-01",
            "is_current": True,
            "industry": "Logistics",
            "responsibilities": "Oversaw daily warehouse dispatch for three shifts.",
            "achievements": "Reduced order-processing errors.",
        },
        {
            "position": "Warehouse Administrator",
            "employer": "Highveld Freight",
            "start_date": "2018-01-15",
            "end_date": "2021-02-28",
            "responsibilities": "Reconciled stock counts and prepared the weekly operations report.",
        },
    ],
    "education": [{
        "qualification": "Diploma in Logistics",
        "institution": "University of Johannesburg",
        "field_of_study": "Supply chain",
        "level": "Diploma",
        "completion_date": "2017-12-01",
    }],
    "certifications": [{
        "name": "SAP ERP Fundamentals",
        "issuing_organization": "SAP",
        "issue_date": "2020-06-01",
    }],
    "languages": ["English", "isiZulu", "Sesotho"],
    "drivers_licence": "Code B",
    "professional_memberships": ["SAPICS"],
    "work_authorization": "South African citizen",
    "target_vacancy_title": "Operations Manager",
}


def _long_cv() -> dict:
    jobs = []
    for index, (title, employer) in enumerate([
        ("Financial Accountant", "Old Mutual"),
        ("Assistant Accountant", "Woolworths"),
        ("Audit Trainee", "Deloitte"),
        ("Accounts Clerk", "City of Cape Town"),
        ("Finance Intern", "Sanlam"),
    ]):
        jobs.append({
            "position": title,
            "employer": employer,
            "location": "Cape Town",
            "industry": "Financial services",
            "start_date": f"{2014 + index * 2}-01-01",
            "end_date": None if index == 4 else f"{2015 + index * 2}-12-01",
            "is_current": index == 4,
            "responsibilities": (
                "Prepared monthly management accounts and variance commentary for the finance committee.\n"
                "Reconciled the general ledger and cleared suspense accounts before close.\n"
                "Supported the external audit with schedules, samples and explanations."
            ),
            "achievements": "Shortened the month-end close." if index % 2 == 0 else "",
        })
    return {
        "full_name": "Sipho Ndlovu",
        "email": "sipho.ndlovu@example.com",
        "phone": "071 555 0199",
        "city": "Cape Town",
        "country": "South Africa",
        "summary": "Finance professional with 11 years of experience across audit and reporting.",
        "skills": ["IFRS", "Excel", "Management accounts", "VAT"],
        "experience": jobs,
        "education": [{
            "qualification": "BCom Accounting",
            "institution": "University of Cape Town",
            "completion_date": "2013-12-01",
        }],
        "certifications": [{"name": "SAICA Training Contract", "issuing_organization": "SAICA"}],
        "languages": ["English", "isiXhosa", "Afrikaans"],
        "drivers_licence": "Code B",
        "target_vacancy_title": "Financial Accountant",
    }


def _pdf_pages(data: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(data))
    return [page.extract_text() or "" for page in reader.pages]


def _pdf_text(data: bytes) -> str:
    return "\n".join(_pdf_pages(data))


def _pdftotext(data: bytes, layout: bool = False) -> str | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
        handle.write(data)
        handle.flush()
        cmd = [exe, "-enc", "UTF-8"]
        if layout:
            cmd.append("-layout")
        cmd += [handle.name, "-"]
        out = subprocess.run(cmd, check=True, capture_output=True)
    return out.stdout.decode("utf-8")


def _assert_order(text: str, headings: list[str]) -> None:
    positions = []
    for heading in headings:
        index = text.find(heading)
        assert index != -1, heading
        positions.append(index)
    assert positions == sorted(positions)


def _docx(data: bytes) -> Document:
    document = Document(io.BytesIO(data))
    xml = document.element.xml
    assert document.tables == []
    assert "w:tbl" not in xml
    assert "w:drawing" not in xml
    assert "w:pict" not in xml
    assert "w:txbxContent" not in xml
    return document


def test_template_catalogue_and_aliases():
    assert [item["id"] for item in list_templates()] == ["classic", "modern", "compact"]
    assert template_style(None)["label"] == "Classic"
    assert template_style("professional") is template_style("classic")
    assert template_style("executive") is template_style("classic")
    assert template_style("academic") is template_style("classic")
    assert template_style("ats_pro") is template_style("compact")
    assert template_style("ats_clean") is template_style("compact")
    assert template_style("no-such-template")["label"] == "Classic"


def test_medium_cv_reads_in_order_for_every_template():
    expected = [
        "Summary", "Experience", "Education", "Skills",
        "Certifications", "Languages", "Memberships", "Additional",
    ]
    for template in ("classic", "modern", "compact", "professional", "ats_clean"):
        pdf = render_cv_pdf(MEDIUM, template)
        assert pdf[:5] == b"%PDF-"
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) == 1
        for page in reader.pages:
            assert list(page.images) == []
        text = _pdf_text(pdf)
        assert text.index("Thandi Mokoena") < text.index("Summary")
        _assert_order(text, expected)
        assert "Operations supervisor with 6 years" in text
        assert "Acme Logistics" in text and "2021" in text and "Present" in text
        if template_style(template)["date_short"]:
            assert "Mar 2021" in text
        else:
            assert "March 2021" in text
        assert "University of Johannesburg" in text and "Supply chain" in text
        assert "English, isiZulu, Sesotho" in text
        assert "Driver's licence: Code B" in text
        assert "South African citizen" in text
        assert "SAPICS" in text
        assert "Photoshop" not in text
        # Nothing was added that the record does not contain.
        assert "photograph" not in text.lower()

        raw = _pdftotext(pdf)
        layout = _pdftotext(pdf, layout=True)
        if raw is not None and layout is not None:
            assert raw.index("Thandi Mokoena") < raw.index("Summary") < raw.index("Experience")
            _assert_order(raw, expected)
            role_line = next(line for line in layout.splitlines() if "Acme Logistics" in line)
            assert "2021" in role_line and "Present" in role_line
            assert "•" in raw

        document = _docx(render_cv_docx(MEDIUM, template))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        joined = "\n".join(paragraphs)
        _assert_order(joined, expected)
        assert any("Acme Logistics" in line and "2021" in line and "Present" in line for line in paragraphs)
        name = next(p for p in document.paragraphs if p.text.strip())
        assert name.runs[0].font.name == "Calibri"
        assert name.runs[0].bold
        section = document.sections[0]
        assert 200 <= section.page_width.mm <= 220
        assert section.left_margin.cm >= 1.3


def test_short_cv_omits_empty_sections_and_invents_nothing():
    short = {
        "full_name": "Amina Diallo",
        "email": "amina@example.com",
        "city": "Dakar",
        "country": "Senegal",
        "experience": [{
            "position": "Graduate Intern",
            "employer": "Port of Dakar",
            "start_date": "2024-02",
            "end_date": "2024-11",
            "responsibilities": "Logged vessel arrivals and prepared the weekly berth report.",
        }],
    }
    text = _pdf_text(render_cv_pdf(short, "classic"))
    assert "Amina Diallo" in text
    assert "Port of Dakar" in text
    assert "February 2024" in text
    assert "November 2024" in text
    for absent in (*HEADINGS[0:1], *HEADINGS[2:], "Present", "Photoshop", "Johannesburg"):
        assert absent not in text
    docx_text = "\n".join(p.text for p in _docx(render_cv_docx(short, "modern")).paragraphs)
    assert "Summary" not in docx_text
    assert "Graduate Intern" in docx_text


def test_long_cv_stays_on_two_pages_without_an_orphaned_heading():
    cv = _long_cv()
    for template in ("classic", "modern", "compact"):
        pdf = render_cv_pdf(cv, template)
        pages = _pdf_pages(pdf)
        assert len(pages) == 2
        for page in pages:
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            assert lines
            assert lines[-1] not in set(HEADINGS)
            assert lines[-1] != "Achievements"
        combined = "\n".join(pages)
        assert "Sanlam" in combined and "Old Mutual" in combined
        assert "University of Cape Town" in combined


def test_a_bullet_that_fits_on_one_page_is_not_split():
    filler = "Prepared the weekly operations pack and checked the variance. " * 40
    marker_start = "ALPHAWORD reconciling the dispatch ledger"
    marker_end = "OMEGAWORD before the Friday close"
    bullet = f"{marker_start} " + ("and checking the count " * 28) + marker_end
    cv = {
        "full_name": "Lerato Khumalo",
        "email": "lerato@example.com",
        "summary": filler,
        "experience": [
            {"position": "Supervisor", "employer": "Acme", "start_date": "2020-01-01",
             "end_date": "2022-01-01", "responsibilities": filler},
            {"position": "Clerk", "employer": "Beta Stores", "start_date": "2022-02-01",
             "is_current": True, "responsibilities": bullet},
        ],
    }
    pages = _pdf_pages(render_cv_pdf(cv, "classic"))
    homes = [i for i, page in enumerate(pages) if "ALPHAWORD" in page]
    assert len(homes) == 1
    assert "OMEGAWORD" in pages[homes[0]]
    assert "BETAWORD" not in "\n".join(pages)


def test_control_characters_and_markup_do_not_break_the_file():
    cv = {
        "full_name": "A\x00 B",
        "summary": "Kept <stock> & records.",
        "skills": ["SQL"],
        "experience": [{
            "position": "Clerk",
            "employer": "Acme",
            "responsibilities": "Counted <items> & bins.",
        }],
    }
    pdf = _pdf_text(render_cv_pdf(cv, "compact"))
    assert "Kept <stock> & records." in pdf or "Kept <stock> &amp; records." not in pdf
    assert "<stock>" in pdf
    assert "&" in pdf
    docx_text = "\n".join(p.text for p in _docx(render_cv_docx(cv, "classic")).paragraphs)
    assert "A  B" in docx_text or "A B" in docx_text
    assert "<stock>" in docx_text


def test_builder_passes_memberships_and_work_authorisation():
    cv = build_tailored_cv({
        "full_name": "A",
        "professional_memberships": ["SAICA"],
        "work_authorization": "South African citizen",
        "languages": ["English"],
        "skills": [],
    }, {})
    assert cv["professional_memberships"] == ["SAICA"]
    assert cv["work_authorization"] == "South African citizen"
    assert cv["languages"] == ["English"]
