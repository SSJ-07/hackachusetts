---
inclusion: auto
name: Visit rules
description: Visit types and their logistics rules — escort, sedation, telehealth eligibility, dialysis, prenatal, chemo, duration and recurrence
---

# Visit-type rulebook semantics

Every rule is **data**, in the rulebook below, so it is auditable and extensible. Code reads
the rulebook; it does not hard-code visit logic.

#[[file:planner/visit_rules.yaml]]

## What each rule means
- **duration** — total visit length in minutes, including prep and recovery. Feeds the
  round-trip reachability check (`minutes`).
- **escort_required** — if true (e.g. sedation for colonoscopy), a **transit-only plan is
  never valid**. The planner must offer an escort-aware ride (PT-1 pre-fill / volunteer
  driver window), never a bus-only itinerary.
- **telehealth_ok** — a telehealth swap may be offered **only** when this is true.
  Procedures (colonoscopy, dialysis, infusion) are false.
- **prep** — whether an in-language prep sheet is attached (from reviewed templates only).
- **recurrence** — e.g. dialysis is 3×/week; the planner must consider the repeating pattern.

## Safety
Logistics only — never clinical advice or eligibility. The planner's output is checked by
properties: escort ⇒ never transit-only, no slot overlaps the work shift (incl. travel),
telehealth only if allowed, no clinical/eligibility text.
