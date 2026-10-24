---
inclusion: always
---

# Journaling — every agent logs its own Kiro usage

The Kiro-usage write-up is assembled from `docs/kiro-journal/<member>.md`. In the
**Kiro IDE/CLI** the hooks in `.kiro/hooks/` log automatically. In **Kiro Crew and
Web the hooks do NOT fire** — so the agent MUST log its own work. This rule is how
Crew "auto-logs": it is injected into every session, so every agent follows it.

## When to log (Crew / Web)
After completing a **meaningful unit of work** — a module or function written, a spec
or steering file added, a bug fixed, an MCP server wired, a test suite made green.
NOT for trivial reads, questions, or a single typo.

## How to log
Run, from the repo root, after the work is verified:

```
python scripts/log_kiro.py --member <member> --tool Crew --topic <spec|pbt|steering|mcp|hooks|power|other> \
  --what "one line — what happened" [--kiro "what Kiro/Crew did"] [--outcome "result + test status/sha"]
```

- `--member` is the human whose work this is (e.g. `sumedh`, `m2-prince`). The entry
  lands in that person's own file, so appends never conflict.
- Log **once per unit of work**, not once per file touched. Keep `--what` to one line.
- The helper creates the member's file on first use; never hand-edit another member's file.

## Rules
- Log only what actually happened and was verified — the journal is evidence, never aspiration.
- Append only. Never rewrite or delete a prior entry.
- Numbers in an entry carry their result (e.g. "252 tests green"), consistent with the
  project's every-number-has-a-source rule.
