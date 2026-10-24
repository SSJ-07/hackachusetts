# ui-planner — Requirements (Requirements-First)

Visit Planner screen in `web/` for a **referral coordinator / navigator** working with a
car-less patient. It turns a visit type and a short logistics barrier check into a ranked,
plain-language plan — a reachable slot, an escort-aware ride, a telehealth swap, a prep
sheet, or a navigator hand-off — plus an itinerary, a phone-sized preview and a PT-1
pre-fill summary.

Owner: M4. Steering: `ui-style.md`, `accessibility.md`, `visit-rules.md`, `product.md`.
Contracts: `docs/contracts.md` §3 (`POST /plan`, `GET /provenance`). Barrier text:
`data/manual/barrier_questions.yaml` (EN + draft ES).

> **Guardrail (product.md):** logistics only. Patient-facing text comes only from
> human-reviewed templates; template-derived numbers are labelled "illustrative". The
> screen never shows clinical advice or eligibility wording. Patients are synthetic.

Each requirement has a stable id (`UP-n`) referenced by tests.

## UP-1 Visit-type picker
1.1 WHEN the screen loads THEN it SHALL show a list of visit types the planner knows and
    SHALL let the navigator pick exactly one before the barrier check.
1.2 The picker SHALL label each type in plain words (no clinical codes).

## UP-2 Barrier check (6 taps)
2.1 The barrier check SHALL present the six questions from `barrier_questions.yaml`
    (`transport`, `work_shift`, `childcare`, `escort`, `cost`, `language`), one concept at
    a time, each answerable with a tap.
2.2 Question text SHALL come from the active locale (`en` / `es`) via the `planner.barrier.*`
    i18n keys; no question text SHALL be hard-coded in the component.
2.3 The answers SHALL map to the `POST /plan` `barriers` shape, including the optional
    `work_shift` and `childcare_window` time windows (VP-20) when the navigator gives them.
2.4 The navigator SHALL be able to go back and change an earlier answer before submitting.

## UP-3 Submit and ranked options
3.1 On submit the screen SHALL call `POST /plan` exactly once with the chosen visit type,
    a synthetic patient and the barrier answers.
3.2 The response's options SHALL render in the fixed contract order
    (`slot` | `ride` | `tele` | `prep` | `none`), each with its plain-language reason
    (`why`) visible.
3.3 Every option SHALL show a reason; an option SHALL NOT render without one.
3.4 WHEN the top option is a `ride` for an escort-required visit THE screen SHALL NOT render
    any transit-only (`slot`) option as the recommended one (visit-rules.md escort rule).

## UP-4 Itinerary and phone preview
4.1 WHEN the plan carries an itinerary with legs THE screen SHALL show the out and return
    legs in order, each leg in plain words (walk / bus, times as HH:MM).
4.2 The screen SHALL show a **phone-sized** preview of the itinerary (a narrow column the
    navigator can read to the patient) built only from the itinerary data.
4.3 `plan_b` text SHALL render only when the API provides it (reviewed templates, M3); the
    screen SHALL NOT synthesize patient-facing fallback text.

## UP-5 PT-1 pre-fill summary
5.1 WHEN `pt1_prefill` is non-empty THE screen SHALL show a summary listing each field and
    its value, and SHALL mark fields left `null` as "for a person to complete".
5.2 The summary SHALL state the PT-1 is a pre-fill draft, not a submitted form.

## UP-6 Provenance drawer
6.1 Clicking any `ProvenanceChip` SHALL open a drawer showing, from `GET /provenance?id`:
    source → vintage → requirement id → each property with its pass/fail/pending status →
    a spec link.
6.2 The drawer SHALL be dismissable by button and by the Escape key, and SHALL return focus
    to the chip that opened it.
6.3 WHILE the drawer is loading or the id is unknown THE drawer SHALL show a loading / not-
    found state, never a blank panel.

## UP-7 States, language, provenance
7.1 The `POST /plan` call SHALL have loading, empty (`none`-only) and error states.
7.2 All copy SHALL come from `en.json` / `es.json` under the `planner.*` namespace; ES SHALL
    have every `planner.*` key EN has.
7.3 Template-derived or not-yet-real numbers SHALL be labelled "illustrative".

## Fast-check properties (web/e2e, axe + Playwright)
- **UP-P1 (escort safety).** For an escort-required visit, the recommended option is never a
  transit-only `slot`. _UP-3.4_
- **UP-P2 (every option has a reason).** Every rendered option shows non-empty reason text.
  _UP-3.3_
- **UP-P3 (ES has no missing keys).** Switching to ES renders the planner flow with no raw
  key strings (every `planner.*` key resolves). _UP-7.2_
- **UP-P4 (not colour-only).** No option's meaning relies on colour alone: each carries a
  text label and an icon/shape. _accessibility.md, UP-3_
- **UP-P5 (a11y).** The planner screen and the open provenance drawer have no serious or
  critical axe violations (WCAG 2.1 AA). _UP-6, accessibility.md_

## Traceability
| Requirement | Verified by |
|---|---|
| UP-1, UP-2 | `web/e2e/planner.spec.ts` (visit type + barrier flow) |
| UP-3, UP-3.4 | `web/e2e/planner.spec.ts::Maria gets an escort ride, never a transit slot` |
| UP-4 | `web/e2e/planner.spec.ts::itinerary + phone preview` |
| UP-5 | `web/e2e/planner.spec.ts::PT-1 summary` |
| UP-6 | `web/e2e/planner.spec.ts::provenance drawer` |
| UP-7.2 | `web/src/i18n/i18n.test.ts` (ES key parity), `web/e2e/planner.spec.ts` (ES run) |
| UP-P1..P5 | `web/e2e/planner.spec.ts`, `web/e2e/a11y.spec.ts` |
