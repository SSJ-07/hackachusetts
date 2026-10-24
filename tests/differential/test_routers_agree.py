"""Differential tests: RAPTOR == CSA == brute force.

The brute-force router is correct by construction on tiny feeds, so it is the
ground-truth oracle. CSA is a structurally different second implementation.
If all three agree on a large sample of random feeds, the router is almost
certainly correct — this is the project's core correctness argument
(steering/tech.md, FINAL §8.3).
"""

from __future__ import annotations

import pytest

from engine import round_trip as raptor_rt
from engine.brute_force import earliest_arrival as bf_ea
from engine.brute_force import round_trip as bf_rt
from engine.csa import earliest_arrival as csa_ea
from engine.csa import round_trip as csa_rt
from engine.raptor import earliest_arrival as raptor_ea
from engine.synth import random_feed

DATE = "2026-11-12"
STARTS = (7 * 3600, 10 * 3600, 14 * 3600, 18 * 3600)
MINUTES = (30, 120)


@pytest.mark.parametrize("seed", range(120))
def test_three_routers_agree_on_reachability(seed: int) -> None:
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    origin, clinic = stops[0], stops[-1]
    for start in STARTS:
        for minutes in MINUTES:
            r = raptor_rt(tt, origin, clinic, DATE, start, minutes).reachable
            c = csa_rt(tt, origin, clinic, DATE, start, minutes).reachable
            b = bf_rt(tt, origin, clinic, DATE, start, minutes).reachable
            assert r == b, f"RAPTOR != brute force at seed={seed} start={start} min={minutes}: {r} vs {b}"
            assert c == b, f"CSA != brute force at seed={seed} start={start} min={minutes}: {c} vs {b}"


@pytest.mark.parametrize("seed", range(120))
def test_earliest_arrival_matches_oracle(seed: int) -> None:
    """Earliest-arrival TIMES (not just reachability) must match the oracle."""
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    origin = stops[0]
    rp = raptor_ea(tt, {origin: 0}, DATE)
    cs = csa_ea(tt, {origin: 0}, DATE)
    bf = bf_ea(tt, {origin: 0}, DATE)
    for stop in stops:
        bf_arr = bf.get(stop, (None,))[0]
        rp_arr = rp.get(stop, (None,))[0]
        cs_arr = cs.get(stop, (None,))[0]
        assert rp_arr == bf_arr, f"RAPTOR arr at {stop} seed={seed}: {rp_arr} vs oracle {bf_arr}"
        assert cs_arr == bf_arr, f"CSA arr at {stop} seed={seed}: {cs_arr} vs oracle {bf_arr}"
