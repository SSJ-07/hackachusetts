# bug-csa-transfer-cap — Tasks

- [x] 1. Reproduce: `tests/differential/test_real_feed_agree.py` on the real PVTA feed — RAPTOR reaches
      21 stops (from origins 1786, 1385) that CSA reports unreachable; CSA never earlier.
- [x] 2. Minimal counterexample: hand-built 5-stop "cap trap" feed (`tests/property/test_csa_transfer_cap.py`);
      pre-fix CSA AND pre-fix brute force lose Y; RAPTOR (and both fixed oracles) reach it at 08:50 with 2 buses.
- [x] 3. Root cause: one label per stop under a bi-criteria (time × buses) constraint (`engine/csa.py`).
- [x] 3b. Brute force (`engine/brute_force.py`) settled each stop once — same bug, same trap feed (Y lost).
- [x] 4. Fix: per-level labels `arr[h][stop]`, boarding from level h writes level h+1, trip reachability
      per (trip, level); result = top level. Brute force: settle per (stop, buses, rode_bus) state.
- [x] 5. Regression tests: `test_csa_transfer_cap.py` (trap feed, cap still respected) and the real-feed
      differential (`make test-full`).
- [x] 6. No regression: synthetic differential (240 feeds + chain feeds), golden PVTA, transfer-limit and
      midnight suites green; real-feed RAPTOR == CSA on 40 round trips + 3 full earliest-arrival maps.
- [ ] 7. Follow-up: add the trap shape to `engine/synth.py::random_feed` so random differential runs can
      generate it (same follow-up as bug-transfer-limit task 7).

Requirements: CS-3, CS-4. Status: **fixed**.
