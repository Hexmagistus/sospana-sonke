"""ATS CV Audit & Rebuild (Sospana Sonke "CV Doctor").

Takes a candidate's ORIGINAL uploaded CV and runs the full professional
pipeline over it:

1. inspect.py   — Phase 1 document-level ATS audit of the original FILE (tables,
                  text boxes, columns, headers/footers, images, fonts, page count).
2. parse.py     — deterministic section parser over the extracted text: contact
                  block, headline, summary, skills, experience entries with dates
                  and bullets, education with completion status, certifications,
                  sensitive personal data.
3. rewrite.py   — conservative, truth-preserving rewrite: weak phrasing removed,
                  tense made consistent, British/SA spelling, acronyms expanded on
                  first use, headline + summary assembled ONLY from facts in the
                  source. Optional Claude polish behind a numeric/claim guard.
4. render.py    — premium single-column ATS-safe DOCX + text-based PDF.
5. scoring.py   — five-area scoring (before and after) with stated basis.
6. stress.py    — Phase 5: re-extracts the generated files' text and verifies
                  reading order, headings, contact, employment and education.
7. directions.py— Phase 7: three evidence-based career directions.

Truthfulness contract (same as the rest of the documents module): nothing is
added that the source CV does not state. Unknowns become checklist questions,
never guesses.
"""
