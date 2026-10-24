---
inclusion: fileMatch
fileMatchPattern: 'web/**'
---

# Accessibility — WCAG 2.2 AA for everything under `web/`

Our users include older adults, low-vision and limited-English patients, and navigators on
shared clinic PCs. Accessibility is a gate, not polish: a File Save hook runs axe-core on
changed components and CI re-runs it.

## Baseline
- Meet **WCAG 2.2 Level AA**. Zero axe-core violations of serious/critical impact.
- Semantic HTML first (`button`, `nav`, `table`, `th scope`); ARIA only to fill gaps.
- Every page has one `h1`, a logical heading order, `lang` set (`en` / `es`), and a
  skip-to-content link.

## Keyboard
- Every action works by keyboard alone, with a visible focus indicator (2.4.7, 2.4.11).
- **Week grid:** arrow keys move between cells; Enter opens the day ribbon; the drag
  what-if has a keyboard equivalent (select block → arrow to new hour → Enter). Dragging
  must never be the only way (2.5.7).
- **Map:** every map interaction has a non-map alternative (town/clinic select lists).
- No keyboard traps; Esc closes drawers and dialogs and returns focus to the trigger.

## Color and contrast
- Text contrast ≥ 4.5:1 (≥ 3:1 for large text); UI components and grid cells ≥ 3:1.
- **Never color alone:** red/green grid cells also carry an icon or pattern and a text
  label ("Can't get there and back" / "Reachable"). Use a color-blind-safe palette.

## Large type and layout
- Large-type mode: everything usable at **200% zoom** and reflows at 320 CSS px (1.4.10).
- Use `rem` units; no fixed-height text containers. Targets ≥ 24×24 px (2.5.8).

## Screen readers
- The grid is a real `<table>` (or `role="grid"`) with row/column headers; each cell has an
  accessible name like "Monday 8 am, 12% of 540 car-less adults can reach".
- Charts and the map have a text summary or data table alternative.
- Live updates (what-if recompute, optimizer result) announce via `aria-live="polite"`.

## Content
- UI strings come from `react-i18next`; patient-facing copy follows
  `equity-and-language.md` (reviewed templates only, grade-6 reading level).
- Respect `prefers-reduced-motion`; no auto-playing animation.
