# Kiro Journal — how we used Kiro to build Slot-to-Stop

This is the team's running log of **how Kiro was used** on this project. It is the raw
material for the required "How Kiro was used" write-up (the judges read this).

- **One shared file.** Everyone appends; git history shows who wrote what and when.
- **Entries are appended, never rewritten.** Add to the bottom.
- **Three ways entries land here:**
  1. **Kiro IDE hooks** (`.kiro/hooks/`) — fire automatically on file save and task finish.
  2. **`scripts/log_kiro.py`** — for Crew / CLI / Web work, where hooks don't fire.
     Run: `python scripts/log_kiro.py --member <name> --tool <IDE|CLI|Web|Crew> \
           --topic <spec|pbt|steering|mcp|hooks|power|other> --what "one line" [--outcome "..."]`
  3. **By hand** — paste an entry in the format below.

Hooks run only in the **Kiro IDE and CLI**, never in Web or Crew — so for Web/Crew
work use the helper script or add the entry by hand.

## Entry format

```
## <date time> · <member> · <tool> · topic: <spec|pbt|steering|mcp|hooks|power|other>
what: <one line — what happened>
kiro: <what Kiro did>
outcome: <result, commit sha if any>
```

The `topic` field maps each entry to one of the seven write-up sections the rules name,
so assembling the final write-up is just grouping by topic.

---
<!-- LOG ENTRIES BELOW — newest at the bottom -->

## 2026-10-24 15:33 · sumedh · Crew · topic: hooks
what: built the Kiro journal: 2 IDE hooks + scripts/log_kiro.py, logging to docs/kiro-journal.md
kiro: Crew authored the hook docs against the on-disk hook schema and a stdlib helper so Web/Crew work is logged too
outcome: helper verified; hooks travel via .kiro/ for teammates in the IDE

## 2026-10-24 15:33 · sumedh · Crew · topic: mcp
what: wired gtfs-mcp round_trip/plan_trip/validate_feed to the engine
kiro: one shared deterministic router every agent calls, on cached GTFS not a live API
outcome: imports clean, routes correctly

## 2026-10-24 15:33 · sumedh · Crew · topic: pbt
what: differential PBT: RAPTOR == CSA == brute-force oracle over 400 random feeds
kiro: the oracle caught two real router bugs (origin foot-transfers, CSA transfer-unlock) during bring-up
outcome: 3,200 agreeing queries; 250 tests green in 0.6s
