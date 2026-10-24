# bug-transfer-limit — Bugfix spec

> Written after the fact. The fix landed in PR #6 (`engine/raptor.py`). This spec
> records how the bug was found, the counterexample, the root cause and the fix,
> so it is traceable from requirement to test.
> Violated requirement: **RT-9** (`.kiro/specs/raptor-router/requirements.md`) —
> "THE engine SHALL use at most `max_transfers` (default 2) vehicle transfers per direction."

## How it was found
The synthetic suites were green (RAPTOR == CSA == brute force on 400 random
feeds), but those feeds are small: no journey there ever needed more than 3 buses.
The first **golden trip on the real PVTA feed** (2026-09-17..12-19 vintage) produced
a journey with 4 outbound and 6 return buses.

### Counterexample 1: real feed (as observed)
`round_trip(PVTA, origin="4107" Holyoke/Summit, clinic="1053" Chestnut/Baystate Medical
Center, date=2026-11-12, start=10:00, minutes=60)`, `max_transfers=2` (≤ 3 buses):

| Leg | From → To | Route | Dep | Arr |
|---|---|---|---|---|
| bus 1 | 4107 → 6093 | R41 | 06:36:05 | 07:00:00 |
| bus 2 | 6093 → 9096 | R29 | 07:25:00 | 07:45:00 |
| bus 3 | 9096 → 5117 | P21 | 08:15:00 | 08:51:00 |
| bus 4 | 5117 → 1053 | P21 | 09:00:00 | 09:05:46 |

Return: **6 buses**. Pre-fix result: `reachable=True`. That's wrong, so the router told a
patient a trip was possible that breaks our own limits.
After the fix: `reachable=False` ("no outbound arriving by 09:50:00"), which is correct.
The Holyoke → Baystate access gap is real.

### Counterexample 2: shrunk by Hypothesis
Property *"no journey uses more than `max_transfers + 1` buses"* over a chain feed of
`n` single-hop routes (`S0 → S1 → … → Sn`, each hop its own route, each departing after
the previous one arrives). Against the pre-fix code it **fails**, and Hypothesis shrinks
it to the minimal case:

```
n=4: reached S4 with 4 buses > 3
```

## Current behaviour (before fix)
1.1 WHEN a journey needs more than `max_transfers + 1` buses THEN RAPTOR still reached the
    destination and reported it reachable.
1.2 WHEN several trips are relaxed inside one round THEN a trip could board at a stop that
    an earlier trip in the **same round** had just improved, so one round added several
    buses.

## Expected behaviour
2.1 WHEN a journey needs more than `max_transfers + 1` buses THE engine SHALL NOT report it
    reachable (RT-9).
2.2 WHEN round *k* runs THE engine SHALL board only from stops reached in round *k−1* (or
    the sources), so round *k* adds exactly the *k*-th bus.

## Unchanged behaviour (must not regress)
3.1 Journeys within the limit keep the same earliest arrival (RAPTOR == CSA == brute force).
3.2 Foot transfers still don't count as vehicle transfers.
3.3 Midnight safety (RT-6), check-in buffer (RT-2), return-after-visit (RT-3) unchanged.
