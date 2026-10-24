# ui-planner — Design

## Data flow
```
Planner.tsx (state machine)
  pick visit type ──► barrier check (6 steps) ──► POST /plan ──► PlanView
                                                                   ├─ OptionList (slot|ride|tele|prep|none)
                                                                   ├─ ItineraryView + PhonePreview
                                                                   └─ Pt1Summary
  any ProvenanceChip click ──► GET /provenance?id ──► ProvenanceDrawer
```

The screen is a small client state machine with three phases: `pick` → `barriers` → `plan`.
No router change; it lives at `#/planner` (already wired in `App.tsx`).

## Modules
| File | Role |
|---|---|
| `web/src/routes/Planner.tsx` | Phase state machine; owns visit type, answers, and the plan request. |
| `web/src/components/BarrierCheck.tsx` | The 6-step tap flow; text from `planner.barrier.*`. |
| `web/src/components/PlanView.tsx` | Renders options, itinerary, phone preview, PT-1 summary. |
| `web/src/components/ProvenanceDrawer.tsx` | Drawer fed by `GET /provenance`; focus-trapped, Esc to close. |
| `web/src/components/ProvenanceChip.tsx` | (exists) extended to open the drawer via a context. |
| `web/src/api/client.ts` | adds `postPlan`, `getProvenance`. |
| `web/src/api/types.ts` | adds `PlanRequest`, `PlanResponse`, `ProvenanceResponse` mirror types. |

## Barrier answers → `barriers` shape
The 6 questions map 1:1 to the `maps_to` keys in `barrier_questions.yaml`:

| question | answer UI | barriers field |
|---|---|---|
| transport | yes / no | `has_transport` |
| work_shift | none / a start+end hour | `work_shift: [s, e] | null` |
| childcare | no / yes + optional window | `childcare` + `childcare_window: [s, e] | null` (VP-20) |
| escort | yes / no | `has_escort` |
| cost | yes / no | `cost_worry` |
| language | en / es | `language` |

The synthetic patient (`id`, `origin_bg`, `lang`) is fixed demo data — the UI never asks
for PHI. `language` defaults to the active UI locale.

## Provenance drawer
`ProvenanceChip` takes an optional `provId`. When present it renders as a button that calls
an `onOpenProvenance(id)` handler supplied via React context from `Planner`. The drawer:
- fetches `GET /provenance?id` on open, shows loading → data / not-found;
- renders source, vintage, requirement id, a property list with a text status badge
  (pass/fail/pending — text + shape, never colour only), and a spec link;
- is an `role="dialog"` with `aria-modal`, closes on a button and on Escape, and restores
  focus to the opening chip (UP-6.2).

## Accessibility (accessibility.md)
- Every interactive element is a real `<button>` / `<input>` with a label.
- The flow is fully keyboard operable; the drawer traps focus and restores it on close.
- Option meaning is text + icon, never colour alone (UP-P4).
- A `.large-type` mode toggles a root class that scales the base font via a CSS variable.
- Contrast uses the theme tokens in `styles/tokens.css`; no fixed hex in components.

## States & safety
- Loading / empty (`none`-only) / error states on the `POST /plan` call (UP-7.1).
- Template-derived or not-real numbers carry an "illustrative" tag (UP-7.3).
- `plan_b` renders only when the API supplies it — no machine-generated patient text.

## Testing
- `web/e2e/planner.spec.ts` — Playwright flow with stubbed `/plan` + `/provenance`
  (Maria → escort ride, itinerary, phone preview, PT-1 summary, drawer, ES run) + axe scan.
- Reuses the same `page.route` stub pattern as `e2e/fixtures.ts`.
