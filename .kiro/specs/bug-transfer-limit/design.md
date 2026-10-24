# bug-transfer-limit — Design

## Root cause
`engine/raptor.py::_run_raptor` kept one `best` dict that every round both **read**
(to decide where a trip can be boarded) and **wrote** (when a trip improved a stop).
RAPTOR's correctness depends on round *k* reading only round *k−1*'s labels. Because
trips are scanned one after another within a round, trip B could board at a stop that
trip A had improved moments earlier in the *same* round. That chained two buses in one
round, so the round count no longer bounded the number of buses.

The synthetic feeds never triggered it: their journeys were short. The dense real PVTA
network has many chained transfers, so it showed up straight away.

## Fix (landed in PR #6)
- Before each round, take a frozen snapshot `reachable_prev` of the stops reached in the
  previous round (initially the sources plus their foot-transfer closure).
- Boarding reads **only** `reachable_prev`; improvements are written to `best`.
- After the round, `reachable_prev` = the stops this round newly improved.
- Foot transfers still relax out of improved stops and are not counted as vehicle legs.

This restores the RAPTOR invariant: after round *k*, every label uses at most *k* buses.

## Why the oracles didn't catch it
Brute force and CSA enforce the limit correctly, but differential testing only compares
answers on the feeds you give it. The random feeds had no journey longer than 3 buses,
so all three routers agreed. Lesson: add a feed *shaped* to stress the limit (the chain
feed), not just random ones, and keep golden trips on the real feed.

## Verification
- `tests/property/test_transfer_limit.py` — chain-feed property with the shrunk
  counterexample pinned as `@example(n=4)`, an oracle agreement check, and the end-to-end
  round-trip symptom.
- `tests/golden/test_pvta_golden.py::test_transfer_limit_enforced_on_real_feed` — the real
  counterexample origins on the live feed (skips without the cached feed).
- Differential suite still green (RAPTOR == CSA == brute force).
