# Design — audit-report-pdf

```
GET /report ──> api/deps.get_audit_data (mock | real)
                   │
                   ├─ real: engine.audit.audit(cube, origins, clinic, community, day)   (= /audit)
                   └─ mock: api/mocks/audit.json, labelled MOCK
                   ▼
           clinic_section()  ─ stdlib html.escape, no template engine dependency
                   ▼
           report_html()     ─ one <section class="clinic"> per clinic, CSS page breaks
                   ▼
   format=html ─> text/html          format=pdf ─> WeasyPrint ─> application/pdf
                                                   (503 if Pango/GTK missing)
```

## Decisions
- **Router-only, no new aggregation.** The page calls the `/audit` engine function, so
  the report cannot drift from the screen (RP-2).
- **WeasyPrint is an optional extra** (`pip install -e ".[report]"`, pinned 70.0). It
  needs Pango system libraries: CI installs them with apt; on Windows install the GTK3
  runtime. Without them the PDF answers 503 and the HTML view still works — nothing faked.
- **No Jinja2.** `html.escape` over every interpolated value keeps the dependency list
  short and makes escaping explicit (RP-6).
- **Clinic names** come from `data/manual/clinic_stops.csv` (the same list as `/clinics`).
