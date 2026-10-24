# Requirements — audit-report-pdf

A CHNA-ready report from the Clinic Audit: one page per clinic, built from the real
`/audit` numbers, with sources and method. Owner: M3.

- **RP-1 (one page per clinic).** `GET /report` SHALL return one page per requested
  clinic (`clinic=` repeatable; default: every clinic in the cube), in cube order.
- **RP-2 (same numbers).** Every number on a page SHALL come from the same
  `engine.audit.audit(...)` call that serves `GET /audit` for that clinic, community and
  day. No copied or hard-coded figures.
- **RP-3 (equity with uncertainty).** Each page SHALL show the four equity splits with
  their 90% interval from `equity_ci`; WHEN `equity_ci` is null the page SHALL say
  "not available", never invent an interval.
- **RP-4 (provenance).** Each page SHALL list every source with its vintage, and a
  method box stating that reachability is not attendance.
- **RP-5 (formats).** `format=pdf` (default) SHALL return `application/pdf`;
  `format=html` SHALL return the same document as HTML. WHEN the PDF engine's system
  libraries are missing, `format=pdf` SHALL answer 503 naming the HTML fallback.
- **RP-6 (guardrails).** Page text SHALL pass `planner.guardrails` (logistics only), and
  all interpolated text SHALL be HTML-escaped. Mock mode SHALL be labelled MOCK.
- **RP-7 (errors).** An unknown clinic SHALL answer 404.

| Req | Verified by (`tests/unit/test_report.py`) |
|---|---|
| RP-1 | `test_real_report_numbers_equal_audit`, `test_pdf_has_one_page_per_clinic` |
| RP-2 | `test_real_report_numbers_equal_audit` |
| RP-3 | `test_real_report_numbers_equal_audit`, `test_section_escapes_untrusted_text` |
| RP-4 | `test_real_report_numbers_equal_audit` |
| RP-5 | `test_pdf_or_honest_503` |
| RP-6 | `test_mock_report_is_labelled_mock`, `test_section_escapes_untrusted_text` |
| RP-7 | `test_unknown_clinic_is_404` |
