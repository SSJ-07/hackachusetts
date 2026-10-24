# ui-week-grid — Tasks

Verified 2026-10-24: `pytest` 396 passed · `vitest` 20 passed · `npm run e2e` 2 passed · `npm run a11y` 2 passed.

- [x] 1. Steering: `accessibility.md` + `ui-style.md` (fileMatch `web/**`).
- [x] 2. Backend: additive `GET /clinics` and `GET /audit/blockgroups` with pytest tests (`tests/unit/test_audit_api.py`). (R1, R2)
- [x] 3. Scaffold `web/` (Vite + React + TS), tokens (`styles/tokens.css`), i18n EN/ES, typed client from OpenAPI (`npm run gen:api` → `api/schema.d.ts`). (R8)
- [x] 4. Pure helpers `lib/scale.ts` + `ProvenanceChip` + loading/empty/error states in `routes/Audit.tsx`. (R3.2, R5.3, R8.1, R8.4)
- [x] 5. `WeekGrid` with drag and keyboard move. (R3, R5.1, R5.2)
- [x] 6. `DayRibbon`, `EquityPanel`, `SuggestPanel` — Suggest calls the real `GET /suggest` (optimizer) instead of a stub. (R4, R6, R7)
- [x] 7. `BlockGroupMap` (MapLibre, numbered `ScaleLegend`, desert outline, text summary) + `routes/Audit.tsx`. (R1, R2, R5.3)
- [x] 8. Property: every grid share is in [0,1] and shown as 0–100% (`lib/scale.test.ts`). (R3.2, R3.3)
- [x] 9. Property: one drag/drop or keyboard move → exactly one `/whatif` call (`components/WeekGrid.test.tsx`). (R5.1, R5.2)
- [x] 10. Property: delta shown = after − before from the responses (`routes/Audit.test.tsx`). (R5.3)
- [x] 11. Property: ES locale has no missing keys vs EN (`i18n/i18n.test.ts`). (R8.2)
- [x] 12. Property: no cell relies on colour only — each has a text value (`routes/Audit.test.tsx`). (R8.3)
- [x] 13. Playwright e2e: pick clinic → grid → move a block (keyboard + drag) → delta (`e2e/audit.spec.ts`). (R1, R3, R5)
- [x] 14. axe-core check: hook #7 `.kiro/hooks/a11y-on-web-save.kiro.hook` + CI `web` job (`e2e/a11y.spec.ts`). Found and fixed 2 serious violations (cell text contrast 1.16:1; `role=img` with focusable children on the map). (accessibility.md)

Open: equity confidence intervals render only once `/audit` sends them (Bryan, ACS margins of error).
