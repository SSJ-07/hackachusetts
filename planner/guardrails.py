"""Runtime guardrail: planner output is logistics only.

Every string the solver emits is checked here. A match raises, so clinical advice or
eligibility wording can never reach a response. The term list is a floor, not a
complete filter; M3 owns the reviewed patient-facing templates.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

BANNED_PATTERNS: tuple[str, ...] = (
    r"\beligib",  # eligible, eligibility
    r"\bineligib",
    r"\bqualif",  # qualify, qualifies, qualified
    r"\bdiagnos",
    r"\bprognos",
    r"\bsymptom",
    r"\bmedical advice\b",
    r"\bclinical advice\b",
    r"\bdosage\b",
    r"\bdose\b",
    r"\bmedication\b",
    r"\bprescri",  # prescribe, prescription
    r"\btreatment\b",
    r"\bcancer\b",
    r"\bsedat",  # logistics text says "escort required", not why medically
)
_BANNED = re.compile("|".join(BANNED_PATTERNS), re.IGNORECASE)


class GuardrailViolation(ValueError):
    """Output contained clinical or eligibility wording."""


def find_banned(text: str) -> list[str]:
    return [m.group(0) for m in _BANNED.finditer(text)]


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for k, v in value.items():
            yield from iter_strings(k)
            yield from iter_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from iter_strings(v)


def assert_logistics_only(value: Any) -> None:
    for text in iter_strings(value):
        hits = find_banned(text)
        if hits:
            raise GuardrailViolation(f"non-logistics wording {hits!r} in: {text!r}")
