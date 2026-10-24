# ui-week-grid — Tasks

- [ ] 1. Steering: `accessibility.md` + `ui-style.md` (fileMatch `web/**`).
- [ ] 2. Backend: additive `GET /clinics` and `GET /audit/blockgroups` with pytest tests. (R1, R2)
- [ ] 3. Scaffold `web/` (Vite + React + TS), tokens, i18n EN/ES, typed client from OpenAPI. (R8)
- [ ] 4. `lib/metrics.ts` pure helpers + `ProvenanceChip` + `AsyncState`. (R3.2, R5.3, R8.1, R8.4)
- [ ] 5. `WeekGrid` with drag and keyboard move. (R3, R5.1, R5.2)
- [ ] 6. `DayRibbon`, `EquityPanel`, `SuggestPanel` (stub client + TODO). (R4, R6, R7)
- [ ] 7. `Map` (MapLibre, numbered legend, desert outline, text summary) + `AuditPage`. (R1, R2, R5.3)
- [ ] 8. Property: every grid share is in [0,1] and shown as 0–100%. (R3.2, R3.3)
- [ ] 9. Property: one drag/drop or keyboard move → exactly one `/whatif` call. (R5.1, R5.2)
- [ ] 10. Property: delta shown = after − before from the responses. (R5.3)
- [ ] 11. Property: ES locale has no missing keys vs EN. (R8.2)
- [ ] 12. Property: no cell relies on colour only (each has a text value). (R8.3)
- [ ] 13. Playwright e2e: pick clinic → grid → move a block → delta. (R1, R3, R5)
- [ ] 14. axe-core check (hook #7 + CI job). (accessibility.md)
