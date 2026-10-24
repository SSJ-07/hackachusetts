# bug-csa-transfer-cap — Design

## Root cause
`engine/csa.py::earliest_arrival` kept one `(arrival, legs, hops)` label per stop and
used that label's `hops` to decide whether a connection may still be boarded. Earliest
arrival is a single criterion; a transfer cap makes the problem **bi-criteria**
(arrival time × buses used). A later arrival with fewer buses can dominate for onward
travel, so a single label is not a sufficient state. RAPTOR does not have this problem:
its round structure *is* the bus-count dimension (round k = at most k buses).

## Fix (`engine/csa.py`)
Keep labels per **vehicle-leg level**: `arr[h][stop]` = earliest arrival at `stop` using
at most `h` buses, for `h = 0 .. max_transfers + 1`.
- Seeds and foot transfers live on level 0; walks relax on the level they start from
  (walks are not vehicle legs).
- A connection boarded from level `h` writes level `h + 1`; trip reachability is tracked
  per `(trip, h)`.
- `improve(h, …)` propagates a better time to every higher level (≤ h semantics), so the
  top level holds the overall best; the result is `arr[max_transfers + 1]`.
- Connections are still scanned once, in departure order; cost ×(levels) = ×3.

This is the standard "CSA with a transfer limit" formulation and is exact, matching
RAPTOR's round semantics label-for-label.

## Brute force had the same bug
`engine/brute_force.py::earliest_arrival` ran Dijkstra over arrival time and settled each
**stop** once. Fixed to settle each **state** `(stop, buses_used, last_leg_was_bus)` once,
skipping states dominated by an already-settled state with no more buses. `best[stop]`
remains the first (earliest) settle of that stop, so the public result is unchanged where
the old code was right.

## Why the synthetic oracle did not catch it
Brute force had the same single-settle bug, so the two oracles agreed with each other and
the random tiny feeds never produced the trap shape (long-first, short-later arrival at a hub with an
onward bus). Lesson logged for the experiments write-up: **differential tests are only
as strong as the inputs**; the real feed is a necessary input, not a bonus. The
real-feed differential now runs in `make test-full` whenever `data/cache/pvta` exists.
