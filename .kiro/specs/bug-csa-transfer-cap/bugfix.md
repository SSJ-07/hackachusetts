# bug-csa-transfer-cap — Bugfix spec

> Found on 2026-10-24 while closing connection-scan task 6 (differential testing over
> the **real** PVTA feed). Violated requirements: **CS-3** (CSA honours the same limits
> as RAPTOR) and **CS-4** (RAPTOR == CSA), `.kiro/specs/connection-scan/requirements.md`.
> The bug was in BOTH oracles — CSA **and** the brute-force router (`engine/brute_force.py`
> settled each stop once) — not in the production router (RAPTOR). Two agreeing oracles
> that under-report reach would have hidden a RAPTOR regression of the same shape.

## How it was found
`tests/differential/test_real_feed_agree.py` compares the full earliest-arrival maps of
RAPTOR and CSA from 3 random PVTA stops at 08:00. Two origins disagreed:

| origin | stops RAPTOR reached | stops CSA reached | mismatched |
|---|---|---|---|
| 1786 | 292 | 280 | 12 (CSA: unreachable) |
| 9801 | 179 | 179 | 0 |
| 1385 | 395 | 386 | 9 (CSA: unreachable) |

In all 21 cases RAPTOR reached the stop (within the 3-bus cap, e.g. stop 7113 at
10:20:27 with 3 buses) and CSA reported it unreachable. CSA was never *earlier*. Round-trip
reachability on 40 random stop pairs agreed (the lost stops were rarely clinic anchors),
which is why the cube and golden suites never showed it.

The synthetic differential suite (240 random tiny feeds + the chain feeds) was green:
the trap needs a stop that is reached *first* by a long journey and *later* by a short one,
with an onward bus after the short arrival. Tiny random feeds almost never contain that;
the dense PVTA network does.

## Counterexample (minimal, hand-built — `tests/property/test_csa_transfer_cap.py`)
```
O -T1-> A -T2-> B -T3-> X      X reached 07:50 with 3 buses (= the cap)
O ------T4------------> X      X reached 08:30 with 1 bus
                        X -T5-> Y   departs 08:40
```
Pre-fix CSA: X's single label = 07:50 / 3 buses; T5 would be a 4th bus → not boarded;
T4's 08:30 arrival does not improve 07:50 → discarded. **Y unreachable.**
Pre-fix brute force: settles X once (07:50, 3 buses) and never re-expands it at 08:30 → **Y unreachable too.**
RAPTOR / fixed CSA / fixed brute force: Y at 08:50 with 2 buses.

## Current behaviour (before fix)
1.1 WHEN the earliest label at a stop has used `max_transfers + 1` buses AND a later label
    with fewer buses exists THEN CSA kept only the earliest label and could not board
    onward, so downstream stops were reported unreachable.

## Expected behaviour
2.1 WHEN a stop is reachable within the cap by ANY combination of arrival time and bus count
    THE CSA router SHALL reach every downstream stop that RAPTOR reaches (CS-3, CS-4).
2.2 FOR every level h ≤ max_transfers + 1, THE CSA router SHALL keep the earliest arrival
    using at most h buses, so boarding decisions never discard a shorter-but-later label.

## Unchanged behaviour (must not regress)
3.1 RAPTOR == CSA == brute force on the synthetic suites (240 feeds + chain feeds).
3.2 No CSA journey exceeds `max_transfers + 1` buses; per-leg time limit unchanged.
3.3 Golden PVTA trips, midnight safety, transfer-limit regression suites unchanged.
