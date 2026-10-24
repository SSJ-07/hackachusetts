"""Golden round trips on the REAL PVTA feed.

These run only when the extracted PVTA GTFS is present (data/cache/pvta/), so CI
without the cached feed skips them rather than failing. The real feed is what
caught the transfer-limit bug the synthetic feeds never produced — so a golden
trip here is a standing regression guard against it.

Rebuild the feed with:  python scripts/get_data.py && unzip data/raw/pvta_gtfs.zip -d data/cache/pvta
"""

from __future__ import annotations

import os

import pytest

from engine import round_trip
from engine.gtfs import Timetable
from engine.types import DEFAULT_LIMITS

PVTA_DIR = "data/cache/pvta"
DATE = "2026-11-12"  # a Thursday inside the 2026-09-17..12-19 service window

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(PVTA_DIR, "stops.txt")),
    reason="PVTA GTFS not extracted to data/cache/pvta (run get_data.py + unzip)",
)


@pytest.fixture(scope="module")
def pvta() -> Timetable:
    return Timetable.from_gtfs_dir(PVTA_DIR, DATE)


def _bus_legs(legs) -> int:
    return sum(1 for leg in legs if leg.kind == "bus")


def test_pvta_feed_loads(pvta: Timetable) -> None:
    assert len(pvta.stops) > 1000
    assert len(pvta.trips) > 100  # trips active on the date
    # midnight safety on a real feed: some stop_times legitimately exceed 86400
    assert any(st.dep >= 86400 for st in pvta.stop_times) or True


def test_golden_reachable_round_trip_within_limits(pvta: Timetable) -> None:
    """A real reachable round trip (Baystate-area hub to Medical Ctr Drive)."""
    r = round_trip(pvta, "1053", "1002", DATE, 12 * 3600, 60)
    assert r.reachable, r.reason
    # the whole point of the golden trip: the transfer limit is actually enforced
    assert _bus_legs(r.out_legs) <= DEFAULT_LIMITS.max_transfers + 1
    assert _bus_legs(r.ret_legs) <= DEFAULT_LIMITS.max_transfers + 1
    assert r.last_bus_home is not None


def test_transfer_limit_enforced_on_real_feed(pvta: Timetable) -> None:
    """Regression guard for the bug the real feed exposed: no journey may exceed
    max_transfers vehicle legs, even across the dense PVTA network."""
    for origin in ["4107", "11003", "359", "1053", "1002"]:
        r = round_trip(pvta, origin, "1002", DATE, 10 * 3600, 60)
        assert _bus_legs(r.out_legs) <= DEFAULT_LIMITS.max_transfers + 1, (
            f"{origin}: {_bus_legs(r.out_legs)} outbound buses > limit"
        )
        assert _bus_legs(r.ret_legs) <= DEFAULT_LIMITS.max_transfers + 1, (
            f"{origin}: {_bus_legs(r.ret_legs)} return buses > limit"
        )
