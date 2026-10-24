# connection-scan — Design

## CSA (`engine/csa.py`)
A *connection* is one vehicle hop from stop A to stop B with a departure and arrival time.
`_connections(tt)` flattens every trip into connections sorted by departure.

`earliest_arrival` scans connections once:
- `reachable_trip[trip]` records where/when we first boarded a trip; once boarded, every
  later connection of that trip is ridable without re-checking the boarding stop (trip
  reachability).
- A connection is also boardable fresh if we are already at its departure stop in time
  (plus the min transfer time when we arrived there by bus).
- On improving a stop's arrival, we relax the transitive foot-transfer closure out of it,
  so a transfer that unlocks a later connection is visible within the single forward scan
  (connections are processed in departure order).
- `hops` tracks vehicle legs used, enforcing the transfer limit.

## Brute force (`engine/brute_force.py`)
A Dijkstra-style label-setting search over `(arrival_time, stop, transfers, rode_bus, legs)`
with a monotonic tiebreaker so leg lists are never compared. The first time a stop is popped
is its optimum. Exhaustive and obviously correct on tiny feeds — the oracle.

## Round-trip assembly
Both routers reuse the same outbound/return framing as RAPTOR (arrive-by outbound,
depart-after return, last-bus-home, earliest-home floor), so the three are directly
comparable field-for-field.
