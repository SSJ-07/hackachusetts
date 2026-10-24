---
inclusion: fileMatch
fileMatchPattern: ["web/src/content/**", "planner/templates/**"]
---

# Equity and language — patient-facing text

These apply when working on patient-facing copy (`web/src/content/**`,
`planner/templates/**`). Wrong or untranslated text is a barrier, not a nicety.

## Reviewed templates only
- Patient-facing text comes **only** from human-reviewed templates, per
  **45 CFR 92.201(c)(3)**. No live machine translation shown to patients.
- Templates live in `planner/templates/{en,es}/*.md`. Each ES file must have a matching EN
  file with the same name and the same placeholders.
- `planner/templates/signoff.json` records the reviewer and a content hash per file.
  **Editing a template invalidates its sign-off**; do not update the hash yourself — a
  human reviewer does. (A Pre Tool Use hook blocks unsigned template writes.)
- Agents may *draft* ES text for review, but drafts are marked `status: draft` and never
  rendered to patients.

## Plain language
- Target a **grade-6 reading level**: short sentences, common words, active voice.
- One idea per sentence. Lead with the action ("Take the 8:15 bus from Main St").
- Times in 12-hour format with am/pm; name the stop and the route number.
- No jargon or abbreviations without expansion ("PT-1" → "MassHealth ride form (PT-1)").

## Languages
- EN and ES are required for every template. Other languages are added only with a
  reviewer.
- Never concatenate translated fragments; use whole-sentence templates with named
  placeholders (`{bus_time}`, `{stop_name}`) so word order works in each language.
- Language choice comes from the patient's stated preference, never inferred from name.

## Guardrails
- **Logistics only.** No clinical advice, no eligibility statements. Use the fixed line
  "Your care team decides your care." / "Su equipo de atención decide su atención."
- **Synthetic patients only** in examples and fixtures (e.g. "Maria", labelled synthetic).
- Any number in copy carries a source + vintage, or is labelled "illustrative".
