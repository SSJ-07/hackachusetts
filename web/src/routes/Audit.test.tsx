import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fc from "fast-check";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Audit } from "./Audit";
import type { AuditCell, AuditResponse, Day } from "../api/types";
import { DAYS, HOURS, blockKey, deltaPts, hourLabel, pct } from "../lib/scale";

/**
 * Audit route properties, with fetch mocked at the network boundary:
 *  (a) a single keyboard move triggers EXACTLY ONE POST /whatif;
 *  (b) the before -> after delta shown equals (after - before) from the
 *      responses, for random before/after shares;
 *  (c) no colour-only cells: every rendered grid cell shows a text value that
 *      matches its share rendered as 0-100%.
 */

const DEMO_SOURCES = [{ name: "ACS", vintage: "2022" }];

/** Build a full 7x12 grid where each cell's share comes from shareFn. */
function fullGrid(shareFn: (day: Day, hour: number) => number): AuditCell[] {
  const cells: AuditCell[] = [];
  for (const day of DAYS) {
    for (const hour of HOURS) {
      const n = 100;
      const share = Math.max(0, Math.min(1, shareFn(day, hour)));
      const reached = Math.round(share * n);
      cells.push({ day, hour, share: reached / n, n, reached });
    }
  }
  return cells;
}

function auditResponse(cells: AuditCell[]): AuditResponse {
  return {
    cells,
    equity: {
      ej: { share: 0.5, n: 10 },
      lep: { share: 0.5, n: 10 },
      age65: { share: 0.5, n: 10 },
      zero_veh: { share: 0.5, n: 10 },
    },
    sources: DEMO_SOURCES,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Install a fetch mock routing by URL + method. Returns a record of calls so a
 * test can count POST /whatif. `whatifFor` maps a what-if request to the audit
 * response the server should return.
 */
function installFetch(opts: {
  auditData: AuditResponse;
  whatifFor: (body: { clinic: string; shift: { block: string; to: number } }) => AuditResponse;
}) {
  const calls: { method: string; url: string; body?: unknown }[] = [];
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, url, body });
    if (url.includes("/clinics")) {
      return jsonResponse({
        clinics: [
          {
            clinic_id: "c1",
            clinic_name: "Demo Clinic",
            visit_type: "primary",
            visit_minutes: 30,
            stop_id: "s1",
            is_demo_anchor: true,
          },
        ],
        sources: DEMO_SOURCES,
      });
    }
    if (url.includes("/whatif") && method === "POST") {
      return jsonResponse(opts.whatifFor(body));
    }
    if (url.includes("/suggest")) {
      // SuggestPanel only fetches /suggest on a button press; default 503.
      return jsonResponse({ detail: "needs real data" }, 503);
    }
    if (url.includes("/audit")) {
      return jsonResponse(opts.auditData);
    }
    return jsonResponse({ detail: "not found" }, 404);
  });
  vi.stubGlobal("fetch", spy);
  return { calls, spy };
}

beforeEach(() => {
  vi.restoreAllMocks();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Audit route — what-if fetch", () => {
  it("fires exactly one POST /whatif per single move (random from != to)", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: HOURS.length - 1 }),
        fc.integer({ min: 0, max: HOURS.length - 1 }),
        async (i, j) => {
          if (i === j) return;
          cleanup();
          vi.unstubAllGlobals();
          const base = fullGrid(() => 0.4);
          const { calls } = installFetch({
            auditData: auditResponse(base),
            whatifFor: () => auditResponse(fullGrid(() => 0.6)),
          });
          const user = userEvent.setup();
          render(<Audit />);
          // Wait for the grid to render.
          const fromBtn = await screen.findByRole("button", {
            name: new RegExp(`Monday ${hourLabel(HOURS[i])}`, "i"),
          });
          fromBtn.focus();
          await user.keyboard("{Enter}");
          const step = i < j ? "{ArrowDown}" : "{ArrowUp}";
          for (let s = 0; s < Math.abs(j - i); s += 1) {
            await user.keyboard(step);
          }
          await user.keyboard("{Enter}");
          await waitFor(() => {
            const whatifCalls = calls.filter(
              (c) => c.method === "POST" && c.url.includes("/whatif"),
            );
            expect(whatifCalls).toHaveLength(1);
          });
        },
      ),
      { numRuns: 15 },
    );
  });

  it("shows a delta equal to after - before from the responses (random shares)", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: 100 }),
        fc.integer({ min: 0, max: 100 }),
        async (beforePct, afterPct) => {
          cleanup();
          vi.unstubAllGlobals();
          const before = beforePct / 100;
          const after = afterPct / 100;
          const fromHour = HOURS[0];
          const toHour = HOURS[1];
          // Base grid: the Monday source block has `before`; everything else 0.3.
          const base = fullGrid((d, h) =>
            d === "mon" && h === fromHour ? before : 0.3,
          );
          // What-if response: the moved block (mon, toHour) now has `after`.
          const whatif = fullGrid((d, h) =>
            d === "mon" && h === toHour ? after : 0.3,
          );
          installFetch({
            auditData: auditResponse(base),
            whatifFor: () => auditResponse(whatif),
          });
          const user = userEvent.setup();
          render(<Audit />);
          const fromBtn = await screen.findByRole("button", {
            name: new RegExp(`Monday ${hourLabel(fromHour)}`, "i"),
          });
          fromBtn.focus();
          await user.keyboard("{Enter}");
          await user.keyboard("{ArrowDown}");
          await user.keyboard("{Enter}");

          const panel = await screen.findByText(/Block moved/i);
          const container = panel.closest(".beforeafter") as HTMLElement;
          const expected = `${deltaPts(before, after)} pts`;
          await waitFor(() => {
            expect(within(container).getByText(new RegExp(expected.replace("+", "\\+")))).toBeInTheDocument();
          });
        },
      ),
      { numRuns: 20 },
    );
  });
});

describe("Audit route — no colour-only cells", () => {
  it("every rendered grid cell shows text matching its share as 0-100%", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.integer({ min: 0, max: 100 }), {
          minLength: DAYS.length * HOURS.length,
          maxLength: DAYS.length * HOURS.length,
        }),
        async (sharePcts) => {
          cleanup();
          vi.unstubAllGlobals();
          let idx = 0;
          const perCellPct = new Map<string, number>();
          const base = fullGrid((d, h) => {
            const p = sharePcts[idx++];
            perCellPct.set(blockKey(d, h), p);
            return p / 100;
          });
          installFetch({
            auditData: auditResponse(base),
            whatifFor: () => auditResponse(base),
          });
          render(<Audit />);
          // Grid present once a known cell renders.
          await screen.findByRole("button", {
            name: new RegExp(`Monday ${hourLabel(HOURS[0])}`, "i"),
          });
          for (const day of DAYS) {
            for (const hour of HOURS) {
              const key = blockKey(day, hour);
              const btn = document.getElementById(`cell-${key}`);
              expect(btn, `cell ${key} should render`).not.toBeNull();
              const text = (btn?.textContent ?? "").trim();
              const expected = pct(perCellPct.get(key)! / 100);
              // Visible text equals the share as a percentage — not colour-only.
              expect(text).toBe(expected);
              expect(text).toMatch(/^\d{1,3}%$/);
            }
          }
        },
      ),
      { numRuns: 15 },
    );
  });
});
