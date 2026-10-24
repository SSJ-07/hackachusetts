#!/usr/bin/env python3
"""Hook #3 — preToolUse (write) template guard.

A write that touches `planner/templates/**` is only allowed if the signoff file
(`planner/templates/signoff.json`) moves with it: either the same write also
touches signoff.json, or signoff.json already shows as modified in the git
working tree. Otherwise exit 2 so the CLI blocks the tool call and the stderr
message is handed back to the model.

The guardrail: a reviewed template is only valid while signoff.json names a
human reviewer for it (45 CFR 92.201(c)(3), AGENTS.md §4). Changing template
copy without re-touching signoff would leave `reviewed: true` asserting a review
that never happened for the new text.

Input: preToolUse JSON on stdin, shape (per Kiro CLI docs):
    {"hook_event_name", "cwd", "tool_name", "tool_input", "tool_response"?}
`tool_input` for a write carries the target path(s); different tools name the
field differently, so we scan a known set of keys plus any string value that
looks like a path.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import PurePosixPath

TEMPLATES_PREFIX = "planner/templates/"
SIGNOFF = "planner/templates/signoff.json"

# tool_input keys that different write tools use for the target path.
_PATH_KEYS = ("path", "file_path", "filePath", "file", "target", "paths", "files")


def _norm(p: str) -> str:
    """Normalise a path to repo-relative POSIX, best effort."""
    p = p.strip().strip('"').strip("'")
    if not p:
        return ""
    # Drop a leading ./ and collapse .. etc. without touching the filesystem.
    try:
        norm = PurePosixPath(p.replace("\\", "/"))
        parts = [seg for seg in norm.parts if seg not in (".",)]
        return "/".join(parts).lstrip("/")
    except Exception:
        return p.replace("\\", "/").lstrip("./")


def _candidate_paths(tool_input: object) -> list[str]:
    out: list[str] = []

    def add(v: object) -> None:
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (list, tuple)):
            for item in v:
                add(item)

    if isinstance(tool_input, dict):
        for k in _PATH_KEYS:
            if k in tool_input:
                add(tool_input[k])
        # Fallback: any string value that smells like a path under the repo.
        if not out:
            for v in tool_input.values():
                if isinstance(v, str) and ("/" in v or v.endswith(".md") or v.endswith(".json")):
                    out.append(v)
    elif isinstance(tool_input, str):
        out.append(tool_input)
    return [_norm(p) for p in out if p]


def _git_modified(cwd: str | None) -> set[str]:
    """Paths with unstaged OR staged changes in the working tree."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "-z"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if res.returncode != 0:
        return set()
    paths: set[str] = set()
    for entry in res.stdout.split("\0"):
        if not entry or len(entry) < 4:
            continue
        # XY<space>path ; rename entries are "R  old\0new" but -z splits them, the
        # "new" path arrives as its own bare entry which we cannot tell apart, so
        # we take the path field after the 3-char status prefix of status entries.
        path = entry[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(_norm(path))
    return paths


def main(argv: list[str] | None = None) -> int:
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except Exception:
        raw = ""

    event: dict = {}
    if raw.strip():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            # Malformed payload: fail open (do not block) but say so on stderr.
            print("guard_templates: could not parse hook JSON; allowing write", file=sys.stderr)
            return 0

    cwd = event.get("cwd")
    targets = _candidate_paths(event.get("tool_input"))

    template_targets = [t for t in targets if t.startswith(TEMPLATES_PREFIX)]
    if not template_targets:
        return 0  # write does not touch templates — nothing to guard

    # Allow when signoff.json is part of the SAME write ...
    if any(t == SIGNOFF for t in targets):
        return 0
    # ... or already modified in the working tree.
    if SIGNOFF in _git_modified(cwd):
        return 0

    listed = ", ".join(sorted(set(template_targets)))
    print(
        "BLOCKED: writing patient-facing template(s) [" + listed + "] without "
        "re-touching " + SIGNOFF + ". A template is only valid while signoff.json "
        "records a human reviewer for it (45 CFR 92.201(c)(3), AGENTS.md §4). "
        "Edit " + SIGNOFF + " in the same change (set reviewed=false until a named "
        "reviewer re-signs).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
