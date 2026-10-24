"""Append one entry to docs/kiro-journal.md — the team's Kiro-usage log.

Used three ways:
  1. Directly, for Crew / CLI / Web work:
       python scripts/log_kiro.py --member sumedh --tool Crew --topic mcp \
         --what "wired gtfs-mcp round_trip to the engine" --outcome "verified, 250 tests green"
  2. By the Kiro IDE hooks in .kiro/hooks/ (they pass the fields the event gives them).
  3. With --stdin, reading a ready-made markdown entry on stdin (what an agent hook does).

Stdlib only; safe to run from any teammate's checkout. Appends only, never rewrites.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "docs" / "kiro-journal.md"

TOPICS = {"spec", "pbt", "steering", "mcp", "hooks", "power", "other"}
TOOLS = {"IDE", "CLI", "Web", "Crew"}


def format_entry(member: str, tool: str, topic: str, what: str, kiro: str, outcome: str) -> str:
    ts = dt.datetime.now().isoformat(timespec="minutes").replace("T", " ")
    lines = [
        f"\n## {ts} · {member} · {tool} · topic: {topic}",
        f"what: {what}",
    ]
    if kiro:
        lines.append(f"kiro: {kiro}")
    if outcome:
        lines.append(f"outcome: {outcome}")
    return "\n".join(lines) + "\n"


def append(entry: str) -> None:
    if not JOURNAL.exists():
        sys.exit(f"ERROR: {JOURNAL.relative_to(ROOT)} not found. Create it first (see its header).")
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(entry)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--member", default="unknown", help="who did the work, e.g. sumedh")
    ap.add_argument("--tool", default="Crew", help="IDE | CLI | Web | Crew")
    ap.add_argument("--topic", default="other", help="spec | pbt | steering | mcp | hooks | power | other")
    ap.add_argument("--what", default="", help="one line: what happened")
    ap.add_argument("--kiro", default="", help="what Kiro did")
    ap.add_argument("--outcome", default="", help="result, commit sha if any")
    ap.add_argument("--stdin", action="store_true", help="read a full markdown entry from stdin instead")
    args = ap.parse_args()

    if args.stdin:
        entry = sys.stdin.read().strip()
        if not entry:
            return  # nothing notable; stay quiet (lets Stop/Save hooks no-op cleanly)
        append("\n" + entry + "\n")
        return

    if not args.what.strip():
        sys.exit("ERROR: --what is required (one line describing what happened).")
    if args.tool not in TOOLS:
        print(f"[warn] unusual --tool '{args.tool}' (expected one of {sorted(TOOLS)})", file=sys.stderr)
    if args.topic not in TOPICS:
        print(f"[warn] unusual --topic '{args.topic}' (expected one of {sorted(TOPICS)})", file=sys.stderr)

    append(format_entry(args.member, args.tool, args.topic, args.what, args.kiro, args.outcome))
    print(f"[ok] logged to {JOURNAL.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
