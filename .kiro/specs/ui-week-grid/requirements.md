# ui-week-grid — Requirements (Quick Spec)

Audit screen in `web/` for a **clinic operations manager**: which clinic hours can car-less
adults reach by bus *and get home the same day*, and what happens if a block moves.

Steering: `ui-style.md`, `accessibility.md`. Contracts: `docs/contracts.md` §3 plus the
additive `GET /clinics` and `GET /audit/blockgroups` (see design.md).

## R1 Clinic picker
1.1 WHEN the screen loads THEN it SHALL call `GET /clinics` and list every clinic by name.
1.2 Selecting a clinic SHALL reload the map, grid, ribbon and equity panel for that clinic.

## R2 Map
2.1 The map SHALL shade each block group by its reachable share for the selected clinic/day.
2.2 Transit deserts (no stop within walk limit) SHALL be outlined and named in the legend.
2.3 The legend SHALL show numeric ranges (e.g. "0–20%"), not colour alone.
2.4 The map SHALL have a text summary for screen readers.

## R3 Week grid
3.1 Rows SHALL be days, columns SHALL be the clinic's hour blocks, from `GET /audit` per day.
3.2 Each cell SHALL print its share as a whole % in 0–100 and carry a `ProvenanceChip`.
3.3 Every share rendered SHALL be in [0, 1] before formatting.
3.4 Each cell SHALL have an accessible name with day, hour, %, and population.

## R4 Day ribbon
4.1 For the selected day the ribbon SHALL show each block on a timeline with its %.
4.2 It SHALL mark the last block from which anyone still gets home by bus.

## R5 Move a block (what-if)
5.1 Dropping a block on another hour in the same day SHALL call `POST /whatif` exactly once.
5.2 Keyboard: Enter picks up a block, ← → choose the hour, Enter drops (one call), Esc cancels.
5.3 The result SHALL show the day's share before → after and the delta, where
    delta = after − before computed from the `/audit` and `/whatif` responses.
5.4 The result SHALL be announced via `aria-live="polite"`.

## R6 Suggest panel
6.1 The panel SHALL call the schedule-suggestion client. While no endpoint exists the client
    SHALL report "not available" and the panel SHALL say so (TODO: `reach-mcp suggest_schedule`).
6.2 Each suggestion SHALL show its shift and gain with sources; "Preview" runs R5's `/whatif`.

## R7 Equity panel
7.1 The panel SHALL render the `equity` field (EJ, limited-English, 65+, zero-vehicle) with
    share, n and an interval when the response carries one.
7.2 If `equity` is absent the panel SHALL not render.

## R8 States, language, provenance
8.1 Every API call SHALL have loading, empty and error states.
8.2 All copy SHALL come from `en.json` / `es.json`; ES SHALL have every EN key.
8.3 No cell SHALL rely on colour only: each shows a text value.
8.4 Every number SHALL show its source via a `ProvenanceChip`.
