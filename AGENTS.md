# AGENTS.md — always-on rules for any agent working in this repo

These rules apply to every agent (Kiro IDE, CLI, Web, Crew) and are shared with other
agent tools that read `AGENTS.md`.

## Non-negotiable guardrails

1. **Logistics only.** Never generate clinical advice or eligibility decisions.
   "Your care team decides your care."
2. **Synthetic patients only.** No real PHI anywhere in code, data, or fixtures.
3. **Every number carries a source and vintage.** Numbers from templates are labelled
   "illustrative" and never stated as findings.
4. **Patient-facing text comes only from human-reviewed templates** (EN + ES), per
   45 CFR 92.201(c)(3). No live machine translation to patients.
5. **No secrets in committed files.** `.kiro/settings/mcp.json` references env vars only;
   real keys live in a git-ignored `.env`.
6. **`.kiro/` is always committed.** Never add it to `.gitignore`.

## Workflow

- `main` is protected. Work on `feat/<area>` branches and merge via PR.
- Contracts live in `docs/contracts.md` and are fixed early; respect those shapes.
- Prefer deterministic, cached data over live third-party routing APIs (use `gtfs-mcp`).
