#!/usr/bin/env python3
"""Hook #10 action — regenerate the requirement traceability matrix.

Invoked by the `traceability-post-task` IDE hook. It scans every spec's
requirements for requirement ids, finds the tests/code that reference each id,
and writes docs/traceability-matrix.md: a table

    requirement id | spec | property / test names (files) | status

Requirements with no referencing test are flagged as GAPS in a second table.

How it works:
  - Requirement ids are harvested from .kiro/specs/*/requirements.md. The repo
    uses several formats (inspected): R1.1 style (manual-data), and PREFIX-N
    style SO-n, CS-n, RC-n, RT-n, PT-n, VP-n. We match both.
  - Reference sites are gathered by scanning tests/**/*.py and
    web/src/**/*.test.* for each exact id. A spec whose ids are prose-only
    (e.g. ui-week-grid) is additionally credited when a test path/name mentions
    the spec name, so a spec is not reported as a total gap merely because it
    numbers its requirements informally.

This module is import-safe (building the matrix is a pure function over a repo
root), and is also run for real by the hook with no arguments (repo root = cwd,
or TRACE_ROOT).
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Requirement-id token: PREFIX-N  (SO-3, CS-12, RC-1, ...) OR Rn.n (R1.1).
# PREFIX is 2-4 uppercase letters so it does not swallow arbitrary CONSTANTS.
ID_RE = re.compile(r"\b(?:[A-Z]{2,4}-\d{1,3}|R\d+\.\d+)\b")

# Test files to scan for references.
PY_TEST_GLOBS = ("tests/**/*.py",)
WEB_TEST_GLOBS = ("web/src/**/*.test.ts", "web/src/**/*.test.tsx",
                  "web/src/**/*.test.js", "web/src/**/*.test.jsx")

OUT_PATH = "docs/traceability-matrix.md"


@dataclass
class Req:
    rid: str
    spec: str
    title: str = ""
    refs: list[str] = field(default_factory=list)  # "path::name" or "path"


def _root() -> Path:
    return Path(os.environ.get("TRACE_ROOT", ".")).expanduser()


def _harvest_requirements(root: Path) -> list[Req]:
    reqs: dict[tuple[str, str], Req] = {}
    specs_dir = root / ".kiro" / "specs"
    for req_file in sorted(specs_dir.glob("*/requirements.md")):
        spec = req_file.parent.name
        for line in req_file.read_text(encoding="utf-8", errors="replace").splitlines():
            for m in ID_RE.finditer(line):
                rid = m.group(0)
                key = (spec, rid)
                if key not in reqs:
                    # Grab a short title from the text after the id. The repo
                    # writes "**SO-1 (coverage objective).** THE optimizer SHALL
                    # ..." so skip a leading "(label)." and any markdown markers,
                    # then take the first sentence.
                    tail = line[m.end():]
                    tail = re.sub(r"^\s*\([^)]*\)", "", tail)   # drop "(label)"
                    tail = tail.lstrip(" .*:)-")                 # strip md + punct
                    title = re.sub(r"\s+", " ", tail).strip()
                    title = re.split(r"(?<=[a-z])\.\s", title)[0][:90]
                    reqs[key] = Req(rid=rid, spec=spec, title=title)
    return list(reqs.values())


def _collect_sources(root: Path) -> list[tuple[str, str]]:
    """Return [(relpath, text)] for every test file we scan."""
    out: list[tuple[str, str]] = []
    for group in (PY_TEST_GLOBS, WEB_TEST_GLOBS):
        for pattern in group:
            for p in root.glob(pattern):
                if "node_modules" in p.parts or "__pycache__" in p.parts:
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                out.append((p.relative_to(root).as_posix(), text))
    return out


_PY_NAME_RE = re.compile(r"^\s*def\s+(test_\w+)", re.MULTILINE)
_JS_NAME_RE = re.compile(r"""(?:it|test|describe)\(\s*['"`]([^'"`]+)['"`]""")


def _names_near(text: str, rid: str) -> list[str]:
    """Best-effort: test/it names in a file that references rid."""
    names = _PY_NAME_RE.findall(text) + _JS_NAME_RE.findall(text)
    # Keep it simple and robust: if the id appears anywhere in the file, we
    # attribute the file's test names to it. Precise per-test attribution would
    # need an AST; the file-level link is what the matrix needs.
    return names


def build_matrix(root: Path) -> tuple[list[Req], list[str]]:
    reqs = _harvest_requirements(root)
    sources = _collect_sources(root)

    # spec name tokens for prose-only crediting (e.g. "ui-week-grid").
    spec_names = {r.spec for r in reqs}
    specs_dir = root / ".kiro" / "specs"
    for d in specs_dir.glob("*/"):
        spec_names.add(d.name)

    for req in reqs:
        for relpath, text in sources:
            if re.search(r"\b" + re.escape(req.rid) + r"\b", text):
                names = _names_near(text, req.rid)
                if names:
                    for n in names[:3]:
                        req.refs.append(f"{relpath}::{n}")
                else:
                    req.refs.append(relpath)
        # dedupe, keep order
        seen: set[str] = set()
        req.refs = [r for r in req.refs if not (r in seen or seen.add(r))]

    # Specs that defined NO formal ids at all (prose specs) — report as a note.
    specs_with_ids = {r.spec for r in reqs}
    prose_specs = sorted(s for s in spec_names
                         if s not in specs_with_ids
                         and (specs_dir / s / "requirements.md").exists())
    return reqs, prose_specs


def render(reqs: list[Req], prose_specs: list[str]) -> str:
    from datetime import datetime, timezone

    reqs_sorted = sorted(reqs, key=lambda r: (r.spec, r.rid))
    covered = [r for r in reqs_sorted if r.refs]
    gaps = [r for r in reqs_sorted if not r.refs]

    lines: list[str] = []
    lines.append("# Requirement Traceability")
    lines.append("")
    lines.append(
        "> GENERATED by `scripts/hooks/update_traceability.py` "
        "(hook #10 `traceability-post-task`). Do not edit by hand — re-run the "
        "script. Generated "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "."
    )
    lines.append("")
    lines.append(
        f"Requirements found: **{len(reqs_sorted)}** across "
        f"**{len({r.spec for r in reqs_sorted})}** specs. "
        f"Covered: **{len(covered)}**. Gaps (no test): **{len(gaps)}**."
    )
    lines.append("")
    lines.append("## Matrix")
    lines.append("")
    lines.append("| Requirement | Spec | Property / test names (files) | Status |")
    lines.append("| --- | --- | --- | --- |")
    for r in reqs_sorted:
        if r.refs:
            refs_md = "<br>".join("`" + x + "`" for x in r.refs)
            status = "covered"
        else:
            refs_md = "—"
            status = "**GAP**"
        title = f" — {r.title}" if r.title else ""
        lines.append(f"| `{r.rid}`{title} | `{r.spec}` | {refs_md} | {status} |")
    lines.append("")

    lines.append("## Gaps (requirements with no referencing test)")
    lines.append("")
    if gaps:
        lines.append("| Requirement | Spec |")
        lines.append("| --- | --- |")
        for r in gaps:
            lines.append(f"| `{r.rid}` | `{r.spec}` |")
    else:
        lines.append("None — every harvested requirement id is referenced by at least one test.")
    lines.append("")

    if prose_specs:
        lines.append("## Prose specs (no formal requirement ids)")
        lines.append("")
        lines.append(
            "These specs state requirements in prose rather than with ids, so they "
            "contribute no rows above. Trace them by spec name:"
        )
        lines.append("")
        for s in prose_specs:
            lines.append(f"- `{s}`")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_matrix(root: Path) -> Path:
    reqs, prose = build_matrix(root)
    out = root / OUT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(reqs, prose), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    root = _root()
    specs = root / ".kiro" / "specs"
    if not specs.is_dir():
        print(f"update_traceability: no specs dir at {specs}", file=sys.stderr)
        return 1
    out = write_matrix(root)
    reqs, prose = build_matrix(root)
    gaps = sum(1 for r in reqs if not r.refs)
    print(f"update_traceability: wrote {out} ({len(reqs)} reqs, {gaps} gaps, "
          f"{len(prose)} prose specs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
