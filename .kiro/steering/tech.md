---
inclusion: always
---

# Tech — stack and coding standards

## Stack
- **Engine:** Python 3.12. RAPTOR / rRAPTOR in NumPy (core). GTFS via `gtfs-kit` / `partridge` + pandas.
- **Oracles:** brute-force Dijkstra over a time-expanded graph (tiny nets), Connection Scan
  Algorithm (second implementation), r5py / Conveyal R5 (reference, optional).
- **Optimizer:** greedy with lazy evaluation + OR-Tools CP-SAT (verifier on tiny cases).
- **Property tests:** Hypothesis.
- **API:** FastAPI. **Storage:** DuckDB + Parquet caches.
- **Frontend:** React + Vite + TypeScript, MapLibre GL + deck.gl (map), D3 (grid/ribbon),
  Tailwind + shadcn/ui, react-i18next.
- **CI:** GitHub Actions + headless Kiro CLI.

## Coding standards
- **Every number carries source + vintage.** No hard-coded findings. A value with no
  provenance is a bug.
- **Times are seconds since local midnight;** GTFS times may exceed 86400 — never wrap them.
- Pure functions in the engine where possible; the router must be testable in isolation.
- Deterministic by default: use cached data and `gtfs-mcp`, not live third-party routing APIs.
- Type hints everywhere in Python; typed API client in the web app generated from
  `docs/contracts.md`.
- Keep secrets out of committed files. `mcp.json` references env vars; real keys live in a
  git-ignored `.env`.

## Correctness bar
The router is safety-relevant (a wrong answer strands a patient). It is covered by
property-based tests and differential tests against the oracles. See `tests/` and the
`raptor-router` spec.
