# engine/

Routing engine and audit computation.

- GTFS ingest + validation → timetable arrays (stops / routes / trips)
- **RAPTOR / rRAPTOR** round-trip router (core)
- **Connection Scan (CSA)** + **brute-force** oracles for differential testing
- Reachability cube (block group × clinic × day × hour → reachable?)
- Greedy schedule optimizer (+ OR-Tools CP-SAT verifier)

Owner: M1 (router + oracles), M2 (cube + optimizer).

Governed by steering `gtfs-domain.md` (fileMatch `engine/**`).
