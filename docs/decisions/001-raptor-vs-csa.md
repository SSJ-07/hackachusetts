# ADR 001 — RAPTOR vs CSA (and why we keep brute force too)

- **Status:** accepted
- **Date:** 2026-10-24
- **Context:** The router is safety-relevant — a wrong answer strands a patient
  (steering/tech.md). We need high confidence it is correct, not just fast.

## Decision
Ship **RAPTOR** as the authoritative router, keep **CSA** as an independent second
implementation, and keep a **brute-force** router as the ground-truth oracle on tiny feeds.
Differential tests assert all three agree.

## Why each

| Router | Role | Strength |
|---|---|---|
| **RAPTOR** (`engine/raptor.py`) | authoritative | round-based; naturally bounds transfers; fast on real feeds; easy to read legs out per round |
| **CSA** (`engine/csa.py`) | second opinion | one departure-ordered scan; structurally different from RAPTOR, so agreement is strong evidence of correctness |
| **brute force** (`engine/brute_force.py`) | oracle | exhaustive label-setting; obviously correct on tiny feeds; the thing the other two are checked against |

## Consequences
- A bug in RAPTOR that CSA does not share (or vice versa) surfaces as a differential
  failure rather than a wrong production answer.
- We pay for three implementations and keep them in sync behind one public signature
  (`round_trip` / `earliest_arrival`). The cost is justified by the safety bar.
- Found during bring-up: RAPTOR initially skipped foot transfers out of the source stops
  (missed walk-only origin→clinic paths); the oracle caught it immediately. CSA initially
  mishandled transfer-unlocked connections. Both were fixed to full three-way agreement
  (240 queries + earliest-arrival equality).

## Alternatives considered
- **r5py / Conveyal R5** as a reference — deferred (optional, §9 cut line). Brute force +
  CSA already give two independent checks.
