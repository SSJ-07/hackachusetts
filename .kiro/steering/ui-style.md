---
inclusion: fileMatch
fileMatchPattern: 'web/**'
---

# UI style — stack, tokens, components, provenance

Applies to everything under `web/`. Pairs with `accessibility.md` (always read both).

## Stack
- **React + Vite + TypeScript** (strict). Function components and hooks only.
- **MapLibre GL** for the map. No basemap tiles from a paid or keyed service.
- **D3 only for scales** (`d3-scale`). React renders the DOM; D3 never touches it.
- **react-i18next** for every string. Locale files in `web/src/i18n/{en,es}.json`; EN and ES
  must have the same keys (a test enforces it).
- Tests: Vitest + Testing Library + fast-check (properties); Playwright + axe-core (e2e, a11y).

## Data
- **All data comes from our API** (`api/`, proxied at `/api`). Never call live third-party
  routing or geocoding APIs (Google, OSRM, Mapbox, …) from the browser.
- Use the typed client in `web/src/api/`. Types are generated from the FastAPI OpenAPI schema
  (`npm run gen:api`); don't hand-write response types that drift from `docs/contracts.md`.
- Every API call has **loading, empty and error** states.

## Design tokens
CSS variables in `web/src/styles/tokens.css`, with a light set on `:root` and a dark set under
`@media (prefers-color-scheme: dark)` and `[data-theme="dark"]`. Components use tokens only —
no literal hex in components.

| Token group | Examples |
|---|---|
| Surface / text | `--bg`, `--surface`, `--text`, `--text-muted`, `--border` |
| State | `--focus-ring`, `--danger`, `--ok`, `--warn` |
| Data scale (5 steps, colour-blind safe) | `--scale-0` … `--scale-4` |
| Space / type | `--space-1` … `--space-6`, `--font-sans`, `--fs-1` … `--fs-5` (rem) |

## Component set (keep it small)
| Component | Job |
|---|---|
| `Map` | block groups shaded by reachable share; transit deserts outlined; numbered legend |
| `WeekGrid` | days × clinic hour blocks; % per cell; drag or keyboard to move a block |
| `DayRibbon` | one day's blocks on a timeline against the last block with a ride home |
| `ProvenanceChip` | source, vintage and link for a number |
| `SuggestPanel` | suggested block shifts with their gain; "apply" previews via `/whatif` |
| `EquityPanel` | EJ / limited-English / 65+ / zero-vehicle split, with intervals when given |

Add a new component only when none of these fits.

## The provenance rule
**Every number on screen shows its source via a `ProvenanceChip` (source, vintage, link).**
A number with no chip is a bug. Numbers that come from templates or stubs are labelled
"illustrative".
