# CI — `.github/workflows/kiro-ci.yml`

The `kiro-ci` workflow runs on every push and PR (all branches). Three jobs:

## `test` — engine + contract tests (Python 3.13)
- `pip install -e ".[dev]" ortools` (+ `mcp/requirements.txt` if present)
- `pytest -q` — the hard gate (unit + property + differential + golden). Failures block the PR.
- **Validate CI workflow YAML** — parses `kiro-ci.yml` with the stdlib `yaml`
  (or `ruby -ryaml` as a fallback). No `pyyaml` is installed into `.venv`.
- **`kiro-cli agent validate`** — runs `kiro-cli agent validate --path <f>` for
  each `.kiro/agents/*.json`, but **only if `kiro-cli` is installed** on the
  runner; otherwise it prints a `::notice::` and skips. Does not change the
  behaviour of the test steps.

## `web` — typecheck + unit + e2e + a11y (Node 24)
`working-directory: web`:
- `npm ci`
- `npx tsc -b`
- `npx vitest run`
- `npx playwright install --with-deps chromium`
- `npm run e2e`  → `playwright test e2e/audit.spec.ts`
- `npm run a11y` → `playwright test e2e/a11y.spec.ts` (axe-core)
- On failure, uploads `web/playwright-report/` as the `playwright-report` artifact.

## `release-gate` — Kiro release-checker gate (headless)
Needs `[test, web]`. Runs the `release-checker` agent headless and fails unless
its output contains `RELEASE: PASS`.

Command (flags **verified** against `kiro-cli 2.34.0` via `kiro-cli chat --help`):

```
kiro-cli chat \
  --no-interactive \
  --agent release-checker \
  --trust-tools=fs_read,execute_bash \
  "<prompt: run the suites, verify RAPTOR==CSA==brute force, end with 'RELEASE: PASS' or 'RELEASE: FAIL'>"
```

| Flag | Source |
|------|--------|
| `--agent <AGENT>` | `kiro-cli chat --help` |
| `--trust-tools=<names>` | `kiro-cli chat --help` |
| `--no-interactive` | `kiro-cli chat --help` |
| `[INPUT]` positional prompt | `kiro-cli chat --help` |
| `kiro-cli agent validate --path <PATH>` | `kiro-cli agent validate --help` |

`--trust-tools=fs_read,execute_bash` are exactly the read-only tools declared in
`.kiro/agents/release-checker.json` (`fs_write` is denied there), so the gate can
run the test suites but cannot modify the repo.

### Authentication — ACTION REQUIRED
`kiro-cli 2.34.0` authenticates **interactively** (`kiro-cli login`: Builder ID /
Identity Center OAuth device flow). It exposes **no documented API-key/token
environment variable or flag** for non-interactive CI auth. The gate is therefore
guarded:

- The step reads `KIRO_API_KEY` from `secrets.KIRO_API_KEY` (never committed).
- If the secret is **absent** (forks / PRs without access), the step emits a
  `::notice::` and exits 0 — the `test` and `web` jobs remain the hard gate.
- If the secret is **present**, the step installs `kiro-cli` and runs the gate.

**What you (the repo owner) must do to enable the gate:**
1. Add a repository secret named `KIRO_API_KEY`
   (Settings → Secrets and variables → Actions → New repository secret).
2. Wire a working **non-interactive** Kiro CLI auth path to that secret, since
   2.34.0 has none out of the box — e.g. a `kiro-cli login` token step, or
   whatever credential mechanism the CLI gains. Update the `env:`/run block in
   the `release-gate` job accordingly.
3. Fill in the **install command** (marked `TODO(install)` in the workflow): no
   public non-interactive installer one-liner was confirmed from `kiro-cli
   --help`; replace the TODO with the documented installer for the runner's
   platform.

Until both the secret and a non-interactive auth path exist, the release gate
self-skips and does not block any PR.
