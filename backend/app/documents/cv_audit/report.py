"""Deliverables 3 & 4 — the ATS audit report and outstanding-information
checklist, rendered to a single PDF (the report is for the candidate, not an
ATS, so a table is fine here)."""
from __future__ import annotations

import io
from datetime import date
from xml.sax.saxutils import escape

from app.documents.cv_audit.render import _pdf_fonts, NAVY, ACCENT, CHARCOAL, MUTED


def main_weaknesses(findings: list[dict], before: dict) -> list[dict]:
    """Concise list: document-level findings first, then the biggest content deductions."""
    out = [{"issue": f["message"], "impact": f["impact"], "severity": f["severity"]}
           for f in sorted(findings, key=lambda f: {"high": 0, "medium": 1, "low": 2}[f["severity"]])]
    topics = {"referee": "references", "personal": "personal", "heading": "headings", "date format": "dates",
              "cliché": "summary", "summary": "summary", "passive": "passive", "first-person": "voice",
              "headline": "headline", "contact": "contact", "fewer than two": "thin", "bullet point(s) run": "long"}

    def topic(msg: str) -> str:
        low = msg.lower()
        return next((t for k, t in topics.items() if k in low), low[:40])

    seen = {topic(o["issue"]) for o in out}
    for key in ("content_quality", "recruitment_effectiveness", "ats_compatibility", "professional_presentation"):
        for b in before["areas"][key]["basis"]:
            if b.startswith("−") and ":" in b:
                msg = b.split(":", 1)[1].strip()
                if topic(msg) in seen:
                    continue
                seen.add(topic(msg))
                out.append({"issue": msg[0].upper() + msg[1:], "impact": _impact_for(key), "severity": "medium"})
    return out[:14]


def _impact_for(area: str) -> str:
    return {
        "content_quality": "Weakens the impression in the first 30 seconds of a recruiter's read.",
        "recruitment_effectiveness": "Makes it harder for a hiring manager to see your value and progression.",
        "professional_presentation": "Looks dated or inconsistent next to competing CVs.",
        "ats_compatibility": "Risks information being lost or mis-filed by screening software.",
    }[area]


def limitations(rebuilt: dict, stress: dict, checklist: list[dict]) -> list[str]:
    out = []
    if stress.get("ats_compliant"):
        out.append("ATS format: fully compliant — every format check on the finished DOCX and PDF passed.")
    for b in stress.get("content_blockers") or []:
        out.append(f"Needed for an ATS-ready CV: {b['message']}")
    if stress.get("length_note"):
        out.append(stress["length_note"])
    failed = [c for c in stress["checks"] if not c["ok"]]
    for c in failed:
        out.append(f"{c['area']}: {c['detail']}")
    if not any(any(ch.isdigit() for ch in b) for e in rebuilt.get("experience", []) for b in e.get("bullets", [])):
        out.append("No measurable results appear in your experience. Nothing was invented, so the recruitment "
                   "effectiveness score stays capped until you add verified figures (see checklist).")
    if any(i["priority"] == "high" for i in checklist):
        out.append("Some details need your confirmation before you send the CV (high-priority checklist items).")
    out.append("Keywords are general for your field. For a specific vacancy, run it through “Tailor my CV to a "
               "job” so the wording is matched to that advert.")
    return out


def render_report_pdf(audit: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

    F = _pdf_fonts()

    def c(rgb):
        return colors.Color(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)

    buf = io.BytesIO()
    name = audit.get("candidate_name") or "Candidate"
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title=f"ATS CV Audit Report — {name}", author="Sospana Sonke")
    t = ParagraphStyle("t", fontName=F["bold"], fontSize=20, leading=24, textColor=c(NAVY))
    sub = ParagraphStyle("s", fontName=F["regular"], fontSize=10, leading=14, textColor=c(MUTED))
    h = ParagraphStyle("h", fontName=F["bold"], fontSize=13, leading=16, textColor=c(NAVY), spaceBefore=14, keepWithNext=1,
                       spaceAfter=5)
    h3 = ParagraphStyle("h3", fontName=F["bold"], fontSize=11, leading=14, textColor=c(ACCENT), spaceBefore=8, keepWithNext=1,
                        spaceAfter=2)
    body = ParagraphStyle("b", fontName=F["regular"], fontSize=10, leading=14, textColor=c(CHARCOAL))
    small = ParagraphStyle("sm", parent=body, fontSize=9, leading=12.5, textColor=c(MUTED))
    bullet = ParagraphStyle("bl", parent=body, leftIndent=12, bulletIndent=1, bulletFontName=F["regular"])

    def bl(text: str):
        return Paragraph(escape(text), bullet, bulletText="•")

    before, after = audit["original_scores"], audit["final_scores"]
    story = [Paragraph("ATS CV Audit Report", t),
             Paragraph(escape(f"{name}  ·  {date.today():%d %B %Y}  ·  Source file: {audit.get('source_filename', '')}"),
                       sub),
             Spacer(1, 8),
             Paragraph(escape(after["disclaimer"]), small)]

    story.append(Paragraph("1. Scores before and after", h))
    rows = [["Area", "Original", "Rebuilt"]]
    for k, a in after["areas"].items():
        rows.append([a["label"], str(before["areas"][k]["score"]), str(a["score"])])
    rows.append(["Overall (weighted)", str(before["overall"]), str(after["overall"])])
    tbl = Table(rows, colWidths=[9.5 * cm, 3 * cm, 3 * cm])
    tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), F["regular"], 10),
        ("FONT", (0, 0), (-1, 0), F["bold"], 10),
        ("FONT", (0, -1), (-1, -1), F["bold"], 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), c(NAVY)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F3F1")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F5F7FA")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DCE5")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)

    story.append(Paragraph("2. Main weaknesses in the original CV", h))
    for w in audit["weaknesses"]:
        story.append(KeepTogether([bl(w["issue"]), Paragraph("Recruitment impact: " + escape(w["impact"]),
                                                             ParagraphStyle("imp", parent=small, leftIndent=12))]))

    story.append(Paragraph("3. Improvements made", h))
    for ch in audit["change_log"]:
        story.append(bl(f"{ch['area']}: {ch['change']}"))
    story.append(bl("Layout: rebuilt as a single-column document with standard headings, contact details in the "
                    "body, real bullet points, one date format, and no tables, text boxes, graphics or photo."))

    story.append(Paragraph("4. ATS stress test on the finished files", h))
    st = audit["stress"]
    story.append(Paragraph(escape(f"{st['passed']} of {st['total']} checks passed. The DOCX and PDF were generated, "
                                  "re-opened, their text extracted and re-parsed to confirm the reading order."), body))
    for chk in st["checks"]:
        mark = "Pass" if chk["ok"] else "Check"
        story.append(bl(f"{mark} — {chk['area']}: {chk['detail']}"))

    story.append(Paragraph("5. Basis of the final scores", h))
    for k, a in after["areas"].items():
        story.append(Paragraph(escape(f"{a['label']} — {a['score']}/100"), h3))
        for b in a["basis"]:
            story.append(bl(b))

    story.append(Paragraph("6. Remaining limitations", h))
    for lim in audit["limitations"]:
        story.append(bl(lim))

    story.append(Paragraph("7. Outstanding information checklist", h))
    story.append(Paragraph("Nothing below has been guessed or filled in for you. Confirm or supply each item, then "
                           "edit the CV on Sospana Sonke and download it again.", small))
    for cat in dict.fromkeys(i["category"] for i in audit["checklist"]):
        story.append(Paragraph(escape(cat), h3))
        for i in [x for x in audit["checklist"] if x["category"] == cat]:
            tag = {"high": "[Priority] ", "medium": "", "low": "[Optional] "}[i["priority"]]
            story.append(KeepTogether([bl(tag + i["item"]),
                                       Paragraph(escape(i["why"]), ParagraphStyle("w", parent=small, leftIndent=12))]))

    if audit.get("directions"):
        story.append(Paragraph("8. Career-positioning options", h))
        story.append(Paragraph("Directions your existing evidence supports. Credentials are common options in the "
                               "South African market — check each vacancy's actual requirements.", small))
        for d in audit["directions"]:
            block = [Paragraph(escape(d["title"]), h3), Paragraph(escape(d["why"]), body),
                     Paragraph("<b>Emphasise:</b> " + escape("; ".join(d["emphasise"])), body),
                     Paragraph("<b>Could strengthen:</b> " + escape("; ".join(d["credentials"])), body),
                     Paragraph("<b>Separate targeted CV:</b> " + escape(d["targeted_cv"]), body)]
            story.append(KeepTogether(block))

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(F["regular"], 8)
        canvas.setFillColor(c(MUTED))
        canvas.drawString(1.8 * cm, 1.0 * cm, "Sospana Sonke · ATS CV Audit · informed assessment, not a vendor rating")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
