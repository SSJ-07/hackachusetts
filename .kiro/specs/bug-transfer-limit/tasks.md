# bug-transfer-limit — Tasks

- [x] 1. Reproduce on the real feed: golden trip 4107 → 1053, 10:00/60 min, gave 4 + 6 buses (limit 3).
- [x] 2. Write a property that fails on the pre-fix code; Hypothesis shrinks it to `n=4` (chain feed, 4 buses).
- [x] 3. Root cause: one `best` dict read and written within a round (`engine/raptor.py::_run_raptor`).
- [x] 4. Fix: board only from the frozen previous-round snapshot `reachable_prev` (PR #6).
- [x] 5. Regression tests: `tests/property/test_transfer_limit.py` (pinned `@example(n=4)`) and
      `tests/golden/test_pvta_golden.py` (real-feed origins).
- [x] 6. Confirm no regression: differential (RAPTOR == CSA == brute force), midnight and golden suites green.
- [ ] 7. Add the chain feed to `engine/synth.py` so random differential runs also stress the limit (follow-up).

Requirement: RT-9. Status: **fixed**.
