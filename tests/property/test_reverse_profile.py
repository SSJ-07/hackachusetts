"""Property test: the reverse profile search (latest_departure) agrees with the
forward search (earliest_arrival).

Invariant: if `latest_departure` says you can leave stop X by time D and still
reach the target by `deadline`, then a forward `earliest_arrival` from X
departing at D must actually arrive at the target no later than `deadline`.
This is the correctness guarantee M2's reachability cube relies on.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from engine import earliest_arrival, latest_departure
from engine.synth import random_feed

DATE = "2026-11-12"


@given(seed=st.integers(min_value=0, max_value=5000),
       deadline=st.integers(min_value=6 * 3600, max_value=23 * 3600))
@settings(max_examples=300, deadline=None)
def test_latest_departure_consistent_with_forward(seed: int, deadline: int) -> None:
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    target = stops[-1]
    ld = latest_departure(tt, {target: deadline}, DATE)
    for stop, (dep, _legs) in ld.items():
        if stop == target:
            continue
        fwd = earliest_arrival(tt, {stop: dep}, DATE)
        arr = fwd.get(target, (None,))[0]
        # the claimed latest departure must really reach the target by the deadline
        assert arr is not None and arr <= deadline, (
            f"seed={seed} stop={stop} latest_dep={dep} forward_arr={arr} deadline={deadline}"
        )


@given(seed=st.integers(min_value=0, max_value=5000))
@settings(max_examples=100, deadline=None)
def test_latest_departure_never_after_deadline(seed: int) -> None:
    """A latest departure can never itself be after the arrival deadline."""
    tt = random_feed(seed)
    stops = sorted(tt.stops)
    target = stops[-1]
    deadline = 18 * 3600
    ld = latest_departure(tt, {target: deadline}, DATE)
    for _stop, (dep, _legs) in ld.items():
        assert dep <= deadline
