#!/usr/bin/env python3
"""Hook #2 — userPromptSubmit reminder.

Prints a short standing reminder that patient-facing text must come only from
reviewed templates. userPromptSubmit hooks surface their stdout to the model as
extra context, so the body of this script is just the message. It never blocks
(exit 0 always) and ignores whatever JSON the CLI puts on stdin.

Guardrail source: AGENTS.md §4, planner/templates/signoff.json, steering
`equity-and-language.md`.
"""
from __future__ import annotations

import sys

REMINDER = (
    "Reminder: patient-facing text only from reviewed templates "
    "(planner/templates, signoff.json). ES stays DRAFT until a named human "
    "reviewer signs off (45 CFR 92.201(c)(3)). Logistics only — never clinical "
    "advice; every number carries a source + vintage."
)


def main(argv: list[str] | None = None) -> int:
    # Drain stdin if present so a piping CLI does not see a broken pipe; we do
    # not need the event payload for a pure reminder.
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass
    print(REMINDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
