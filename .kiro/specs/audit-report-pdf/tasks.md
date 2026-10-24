# Tasks — audit-report-pdf

- [x] 1. Spec: requirements (RP-1..RP-7) + design.
- [x] 2. `api/routers/report.py`: `GET /report` (pdf | html), one page per clinic from
      `engine.audit.audit`, equity CIs, sources + vintages, method box. Wired in `api/main.py`.
- [x] 3. WeasyPrint as optional extra `.[report]` (pinned 70.0); CI installs Pango via apt.
- [x] 4. `tests/unit/test_report.py`: numbers equal `/audit` cell-for-cell, one page per
      clinic, escaping, MOCK label, 404, PDF or honest 503.
- [~] 5. Render a real PDF locally. Blocked on this Windows machine: the GTK3 runtime
      (Pango) is not installed, so the PDF test skips here and runs in CI.
- [x] 6. content-reviewer agent pass on the report text (see `docs/kiro-journal/m3-bryan.md`).
