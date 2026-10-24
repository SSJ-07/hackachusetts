# Tasks — Manual Data Collection (M3)

Branch: `M3-Bryan`. Owner: M3. `[x]` done · `[ ]` open · `[~]` scaffold only.

## 1. Clinic schedules (R1)
- [x] 1.1 Create `data/manual/clinic_schedules.csv` with 18 labelled demo slots.
- [ ] 1.2 Replace demo slots with real posted hours where a clinic publishes them;
  keep `is_template=TRUE` + FICTIONAL label on any that stay synthetic. _(source: clinic websites)_
- [ ] 1.3 Confirm every `clinic_id` matches M2's cube keys. _(coordinate with M2)_

## 2. Rural options (R2)
- [x] 2.1 Create `data/manual/rural_options.csv` — 48 Franklin + Hampshire towns, with
  `county` column; FRTA dial-a-ride cited from frta.org sources.
- [ ] 2.2 **[MANUAL]** Phone each town's Council on Aging; fill `coa_driver` + `hours`,
  set `verified_by` + `date`. _Why manual: COA volunteer-driver programs are not
  published machine-readably._
- [ ] 2.3 Confirm PVTA vs FRTA coverage for the Hampshire towns marked `PVTA ... + TODO-VERIFY DR`.

## 3. PT-1 fields (R3)
- [x] 3.1 Create `data/manual/pt1_fields.json` from mass.gov bulletins; verified fields
  flagged, reconstructed fields `verified:false`.
- [ ] 3.2 **[MANUAL]** Open the live PT-1 form (provider portal) and confirm field
  labels, required flags, transport-mode enum, and recurrence handling. _Why manual:
  mass.gov returns HTTP 403 to automated fetch._
- [ ] 3.3 Resolve PT-1 vs Medical Necessity Form (MNF) field split. _(read current regs)_

## 4. Barrier questions (R4)
- [x] 4.1 Create `data/manual/barrier_questions.yaml` — 6 questions, EN + ES draft,
  mapped to `/plan` barrier keys, each with a source + `verbatim:false`.
- [ ] 4.2 **[MANUAL]** Replace paraphrases with verbatim item text from the AHC HRSN and
  PRAPARE PDFs where a match exists; set `verbatim:true`. _Why manual: exact wording is
  in the source PDFs._
- [ ] 4.3 **[MANUAL]** Bilingual reviewer approves the ES wording.

## 5. Visit rulebook (R5)
- [x] 5.1 Create `planner/visit_rules.yaml` — 4 visit types; sourced flags correct,
  assumptions labelled.
- [ ] 5.2 **[MANUAL]** Clinical-ops confirms durations (colonoscopy 180, chemo chair
  time), dialysis escort/prep flags, and all prenatal fields. _Why manual: clinic
  protocol facts, not published data._

## 6. Patient templates (R6)
- [x] 6.1 Create `planner/templates/{en,es}/itinerary.md` + `prep_sheet.md` at grade-6,
  token placeholders, logistics only.
- [x] 6.2 Create `planner/templates/signoff.json`, every template `reviewed:false`.
- [ ] 6.3 **[MANUAL]** Bilingual human reviewer signs off each template; set
  `reviewed:true`, fill `reviewer` + `date`. _Why manual: 45 CFR 92.201(c)(3) requires
  human-reviewed patient text._
- [ ] 6.4 Run a reading-level check (target grade-6) on EN + approved ES.

## 7. Fact-check list (R7)
- [x] 7.1 Create `docs/sources.md` — 5 `(verify)` claims, candidate sources, statuses.
- [ ] 7.2 **[MANUAL]** Lock one citable FIT follow-up rate (candidate: 50% @ 6mo,
  PubMed 39843790) and mark it `verified`.
- [ ] 7.3 **[MANUAL]** Read the Baystate CHNA PDF and cite the transportation page.
- [ ] 7.4 **[MANUAL]** Confirm current MassHealth flexible-services scope + date.
- [ ] 7.5 **[MANUAL]** Confirm CMS dialysis dataset shift fields from its data dictionary.
- [ ] 7.6 **[MANUAL]** Confirm per-clinic sedated-discharge escort policy (may need a call).

## 8. FRTA mini-GTFS (R8, stretch)
- [~] 8.1 Scaffold `data/manual/frta_minigtfs/` with `agency.txt` + README.
- [ ] 8.2 **[MANUAL]** Pick 1–2 Greenfield-anchored routes; transcribe `stops/routes/
  calendar/trips/stop_times` from the FRTA PDF timetables (past-midnight times as
  `24:00:00`+). _Why manual: timetables are un-fetchable PDFs; stops need geocoding._
- [ ] 8.3 Validate the feed with `gtfs-kit`/`partridge` before engine use.

## 9. Provenance gate (R9)
- [x] 9.1 Every artifact ends with a MISSING / MANUAL-CHECK section.
- [ ] 9.2 Add a repo check (CI) that fails if a data row lacks a `source*` value where
  the schema requires one. _(coordinate with M4's contract tests)_

---
### Legend
**[MANUAL]** = a human step automation cannot close (phone call, PDF read, clinical
confirmation, bilingual sign-off, or a 403/anti-bot-blocked source).
