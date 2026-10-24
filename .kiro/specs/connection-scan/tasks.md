# connection-scan — Tasks

- [x] 1. Brute-force oracle over a connection graph (`engine/brute_force.py`).
- [x] 2. CSA with trip reachability + transfer closure (`engine/csa.py`).
- [x] 3. Differential tests: RAPTOR == CSA == brute force on reachability (`tests/differential/`).
- [x] 4. Differential tests: identical earliest-arrival times, not just reachability.
- [x] 5. ADR comparing the two routers (`docs/decisions/001-raptor-vs-csa.md`).
- [x] 6. Differential over the real PVTA feed: `tests/differential/test_real_feed_agree.py` — RAPTOR == CSA on 40 random stop pairs (reachability) and full earliest-arrival maps from 3 origins; runs in `make test-full` when `data/cache/pvta` is present.

Status: **complete on synthetic feeds** — 240 agreeing round-trip queries plus
earliest-arrival equality across 120 random feeds.
