"""Plan B text for the itinerary, from human-reviewed templates only (spec: VP-23).

Templates: planner/templates/<lang>/plan_b.md, one `## <situation>` section each. A
template is used ONLY when planner/templates/signoff.json marks it reviewed=true
(45 CFR 92.201(c)(3)): no reviewed template -> plan_b stays None. Never machine-
translated at runtime, never falls back to another language.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "planner" / "templates"
SIGNOFF = TEMPLATES / "signoff.json"
SITUATIONS = frozenset({"later_bus", "last_bus"})
_TOKEN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class PlanBTemplateError(ValueError):
    """A plan_b template is malformed or a token is missing."""


def parse_sections(text: str) -> dict[str, str]:
    body = _COMMENT.sub("", text)
    sections: dict[str, str] = {}
    for chunk in re.split(r"^##\s+", body, flags=re.MULTILINE)[1:]:
        name, _, rest = chunk.partition("\n")
        name = name.strip()
        if name in sections:
            raise PlanBTemplateError(f"duplicate section {name!r}")
        sections[name] = " ".join(rest.split())
    missing = SITUATIONS - set(sections)
    if missing:
        raise PlanBTemplateError(f"missing sections {sorted(missing)}")
    return sections


def _reviewed(signoff: Mapping, rel_path: str) -> bool:
    for t in signoff.get("templates", []):
        if t.get("path") == rel_path:
            return t.get("reviewed") is True and bool(t.get("reviewer"))
    return False


def load_plan_b(
    lang: str, templates_dir: Path = TEMPLATES, signoff_path: Path = SIGNOFF
) -> dict[str, str] | None:
    """Sections of the signed plan_b template for `lang`, or None if not signed/absent."""
    if lang not in ("en", "es"):
        return None
    path = templates_dir / lang / "plan_b.md"
    if not path.is_file() or not signoff_path.is_file():
        return None
    signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
    if not _reviewed(signoff, f"planner/templates/{lang}/plan_b.md"):
        return None
    return parse_sections(path.read_text(encoding="utf-8"))


def render(sections: Mapping[str, str], situation: str, values: Mapping[str, str]) -> str:
    if situation not in sections:
        raise PlanBTemplateError(f"no section {situation!r}")

    def fill(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise PlanBTemplateError(f"missing token {key!r} for {situation!r}")
        return str(values[key])

    return _TOKEN.sub(fill, sections[situation])
