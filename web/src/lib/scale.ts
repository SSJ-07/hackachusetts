import { scaleQuantize } from "d3-scale";
import type { Day } from "../api/types";

export const DAYS: Day[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
/** Clinic hours 07..18 inclusive (contracts.md: hour 7..18). */
export const HOURS: number[] = Array.from({ length: 12 }, (_, i) => i + 7);

/** D3 quantize scale: share 0..1 -> one of 5 colour-blind-safe steps (0..4). */
const stepScale = scaleQuantize<number>().domain([0, 1]).range([0, 1, 2, 3, 4]);

/** Returns the scale step index 0..4 for a share in [0,1]. */
export function scaleStep(share: number): number {
  return stepScale(Math.max(0, Math.min(1, share)));
}

/** CSS vars for a cell at a given share, or the "no data" pair when share is null. */
export function cellVars(share: number | null): {
  "--cell-bg": string;
  "--cell-ink": string;
} {
  if (share == null) {
    return { "--cell-bg": "var(--scale-na)", "--cell-ink": "var(--scale-na-ink)" };
  }
  const s = scaleStep(share);
  return {
    "--cell-bg": `var(--scale-${s})`,
    "--cell-ink": `var(--scale-${s}-ink)`,
  };
}

/** 0.123 -> "12%". */
export function pct(share: number): string {
  return `${Math.round(share * 100)}%`;
}

/** 0.123 -> "+12" / "-3" percentage points. */
export function deltaPts(before: number, after: number): string {
  const d = Math.round(after * 100) - Math.round(before * 100);
  return `${d > 0 ? "+" : ""}${d}`;
}

/** 8 -> "8 am", 13 -> "1 pm" (12-hour, am/pm per equity-and-language.md). */
export function hourLabel(hour: number): string {
  const ampm = hour < 12 ? "am" : "pm";
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${h12} ${ampm}`;
}

/** (mon, 8) -> "mon-08" — the /whatif block key. */
export function blockKey(day: Day, hour: number): string {
  return `${day}-${String(hour).padStart(2, "0")}`;
}
