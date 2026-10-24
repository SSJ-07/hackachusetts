#!/usr/bin/env python3
"""Hook #5 — postToolUse (@gtfs-mcp) provenance logger.

After a @gtfs-mcp tool call, append one JSON line to docs/provenance-log.jsonl so
every piece of transit data used can be traced to the call that produced it
(AGENTS.md §3, "every number carries a source and vintage").

Appended record:
    {"ts", "tool", "input", "sources"?, "session"}
- ts      : ISO-8601 UTC timestamp (recorded here, not from the payload)
- tool    : tool_name from the event
- input   : tool_input from the event
- sources : tool_response.sources if the response carries them, else omitted
- session : session id if present in the event, else null

postToolUse hooks are observational — this never blocks. It always exits 0, even
on a malformed payload (a logging hook must not break the tool that just ran).
Input: postToolUse JSON on stdin.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path

LOG_PATH_DEFAULT = "docs/provenance-log.jsonl"


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_sources(tool_response: object) -> object | None:
    """Pull a `sources` field out of the tool response if present."""
    if isinstance(tool_response, dict):
        if "sources" in tool_response:
            return tool_response["sources"]
        # Some MCP responses wrap content; look one level into a dict 'content'.
        content = tool_response.get("content")
        if isinstance(content, dict) and "sources" in content:
            return content["sources"]
    return None


def _log_path(event: dict) -> Path:
    override = os.environ.get("PROVENANCE_LOG")
    if override:
        return Path(override)
    cwd = event.get("cwd")
    base = Path(cwd) if cwd else Path.cwd()
    return base / LOG_PATH_DEFAULT


def main(argv: list[str] | None = None) -> int:
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except Exception:
        raw = ""

    if not raw.strip():
        return 0

    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        print("log_provenance: could not parse hook JSON; nothing logged", file=sys.stderr)
        return 0
    if not isinstance(event, dict):
        return 0

    record: dict = {
        "ts": _utc_now_iso(),
        "tool": event.get("tool_name"),
        "input": event.get("tool_input"),
        "session": event.get("session_id") or event.get("session") or None,
    }
    sources = _extract_sources(event.get("tool_response"))
    if sources is not None:
        record["sources"] = sources

    path = _log_path(event)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"log_provenance: could not append to {path}: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
