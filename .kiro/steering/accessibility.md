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
- **Full keyboard operation.** Every action works by keyboard alone (2.1.1), no traps (2.1.2).
- **Every drag action has a keyboard equivalent** — dragging is never the only way (2.5.7).
- **Visible focus** on every focusable element: a ≥ 2px outline using `--focus-ring`, never
  `outline: none` without a replacement, and focus is never hidden by sticky UI (2.4.7, 2.4.11).
- **Week grid:** arrow keys move between cells; Enter picks up a block, arrows choose the
  new hour, Enter drops it (one `/whatif` call), Esc cancels.
- **Map:** every map interaction has a non-map alternative (town/clinic select lists).
- No keyboard traps; Esc closes drawers and dialogs and returns focus to the trigger.

## Labels
- **Every control has a label**: visible `<label>` for inputs and selects, text or
  `aria-label` for icon buttons (1.3.1, 3.3.2, 4.1.2). Placeholder text is not a label.

## Color and contrast
- **Text contrast ≥ 4.5:1** (≥ 3:1 for large text); UI components and grid cells ≥ 3:1.
  Check both the light and dark token sets.
- **Never colour-only meaning (1.4.1).** Always pair colour with a label, a pattern or a
  number: every grid cell prints its % value, every map class has a numbered legend entry,
  and transit deserts are outlined *and* named in the legend. Use a colour-blind-safe palette.

## Large type and layout
- Large-type mode: everything usable at **200% zoom** and reflows at 320 CSS px (1.4.10).
- Use `rem` units; no fixed-height text containers. Targets ≥ 24×24 px (2.5.8).

## Screen readers
- The grid is a real `<table>` (or `role="grid"`) with row/column headers; each cell has an
  accessible name like "Monday 8 am, 12% of 540 car-less adults can reach".
- Charts and the map have a text summary or data table alternative.
- Live updates (what-if recompute, optimizer result) announce via `aria-live="polite"`.

## Content
- UI strings come from `react-i18next` locale files (EN + ES); no hard-coded copy.
- **Grade-6 reading level for all user-facing copy** — short sentences, everyday words.
  Patient-facing copy also follows `equity-and-language.md` (reviewed templates only).
- Respect `prefers-reduced-motion`; no auto-playing animation.
