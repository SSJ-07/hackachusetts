import { describe, expect, it } from "vitest";
import fc from "fast-check";
import {
  HOURS,
  blockKey,
  deltaPts,
  hourLabel,
  pct,
  scaleStep,
} from "./scale";

describe("scaleStep", () => {
  it("maps any share in [0,1] to an integer step 0..4", () => {
    fc.assert(
      fc.property(fc.double({ min: 0, max: 1, noNaN: true }), (s) => {
        const step = scaleStep(s);
        return Number.isInteger(step) && step >= 0 && step <= 4;
      }),
    );
  });

  it("clamps out-of-range shares", () => {
    expect(scaleStep(-1)).toBe(0);
    expect(scaleStep(2)).toBe(4);
  });

  it("is monotonic non-decreasing in share", () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 1, noNaN: true }),
        fc.double({ min: 0, max: 1, noNaN: true }),
        (a, b) => {
          const [lo, hi] = a <= b ? [a, b] : [b, a];
          return scaleStep(lo) <= scaleStep(hi);
        },
      ),
    );
  });
});

describe("formatting", () => {
  it("pct rounds to whole percent", () => {
    expect(pct(0.125)).toBe("13%");
    expect(pct(0)).toBe("0%");
    expect(pct(1)).toBe("100%");
  });

  it("deltaPts signs the change in percentage points", () => {
    expect(deltaPts(0.1, 0.25)).toBe("+15");
    expect(deltaPts(0.25, 0.1)).toBe("-15");
    expect(deltaPts(0.2, 0.2)).toBe("0");
  });

  it("hourLabel uses 12-hour am/pm", () => {
    expect(hourLabel(7)).toBe("7 am");
    expect(hourLabel(12)).toBe("12 pm");
    expect(hourLabel(13)).toBe("1 pm");
    expect(hourLabel(18)).toBe("6 pm");
  });

  it("HOURS is 07..18 inclusive", () => {
    expect(HOURS[0]).toBe(7);
    expect(HOURS[HOURS.length - 1]).toBe(18);
    expect(HOURS).toHaveLength(12);
  });

  it("blockKey zero-pads the hour", () => {
    expect(blockKey("mon", 8)).toBe("mon-08");
    expect(blockKey("fri", 18)).toBe("fri-18");
  });
});
