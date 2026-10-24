import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fc from "fast-check";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SuggestPanel } from "./SuggestPanel";
import type { AuditCell, Day, SuggestResponse } from "../api/types";
import { HOURS, blockKey, deltaPts, pct } from "../lib/scale";

/**
 * SuggestPanel behaviour, fetch mocked at the boundary:
 *  - the Suggest button issues GET /suggest with the ticked blocks and k=3;
 *  - each change renders gain_people + gain_visit_hours and a chip per source;
 *  - a source with illustrative:true flags the suggestion as illustrative;
 *  - Preview runs POST /whatif and shows a before -> after delta equal to
 *    (after - before) from the responses (random shares);
 *  - a 503 shows the honest "needs real data" message, not a generic error.
 */

const DAY: Day = "mon";

function monCells(shareByHour: (hour: number) => number): AuditCell[] {
  return HOURS.map((hour) => {
    const n = 100;
    const reached = Math.round(shareByHour(hour) * n);
    return { day: DAY, hour, share: reached / n, n, reached };
  });
}

function suggestResponse(over: Partial<SuggestResponse> = {}): SuggestResponse {
  return {
    clinic: "c1",
    day: DAY,
    k: 3,
    baseline_score: 1,
    suggested_score: 2,
    baseline_blocks: [7, 8, 9],
    suggested_blocks: [7, 8, 17],
    open_hours: [17],
    changes: [
      {
        change: { kind: "move_block", day: DAY, block: "mon-09", to: 17 },
        gain_people: 12,
        gain_visit_hours: 3.5,
        sources: [{ name: "GTFS", vintage: "2024" }],
      },
    ],
    sources: [{ name: "GTFS", vintage: "2024" }],
    ...over,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SuggestPanel", () => {
  it("GETs /suggest with the ticked blocks and k=3", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        calls.push(String(input));
        return jsonResponse(suggestResponse());
      }),
    );
    const user = userEvent.setup();
    render(<SuggestPanel clinic="c1" day={DAY} cells={monCells(() => 0.3)} />);
    await user.click(screen.getByRole("button", { name: /suggest changes/i }));
    await waitFor(() => {
      const u = calls.find((c) => c.includes("/suggest"));
      expect(u).toBeDefined();
      const url = new URL(u!, "http://x");
      expect(url.searchParams.get("clinic")).toBe("c1");
      expect(url.searchParams.get("day")).toBe("mon");
      expect(url.searchParams.get("k")).toBe("3");
      // defaults to the first three clinic hours: 7,8,9
      expect(url.searchParams.get("blocks")).toBe("7,8,9");
    });
  });

  it("renders gain_people, gain_visit_hours and a chip per source", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(suggestResponse())),
    );
    const user = userEvent.setup();
    render(<SuggestPanel clinic="c1" day={DAY} cells={monCells(() => 0.3)} />);
    await user.click(screen.getByRole("button", { name: /suggest changes/i }));
    expect(await screen.findByText(/\+12 more car-less adults/i)).toBeInTheDocument();
    expect(screen.getByText(/\+3\.5 visit-hours/i)).toBeInTheDocument();
    expect(screen.getByText(/GTFS/)).toBeInTheDocument();
    // not illustrative here
    expect(screen.queryByText(/Illustrative/i)).not.toBeInTheDocument();
  });

  it("flags a suggestion illustrative when any source is illustrative", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          suggestResponse({
            changes: [
              {
                change: { kind: "move_block", day: DAY, block: "mon-09", to: 17 },
                gain_people: 5,
                gain_visit_hours: 1,
                sources: [
                  { name: "GTFS", vintage: "2024" },
                  { name: "Placeholder", vintage: "n/a", illustrative: true },
                ],
              },
            ],
          }),
        ),
      ),
    );
    const user = userEvent.setup();
    render(<SuggestPanel clinic="c1" day={DAY} cells={monCells(() => 0.3)} />);
    await user.click(screen.getByRole("button", { name: /suggest changes/i }));
    expect(await screen.findByText(/Illustrative/i)).toBeInTheDocument();
  });

  it("shows the 'needs real data' message on a 503 (mock mode)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "needs real data" }, 503)),
    );
    const user = userEvent.setup();
    render(<SuggestPanel clinic="c1" day={DAY} cells={monCells(() => 0.3)} />);
    await user.click(screen.getByRole("button", { name: /suggest changes/i }));
    expect(await screen.findByText(/need real data/i)).toBeInTheDocument();
  });

  it("empty changes list shows the empty state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(suggestResponse({ changes: [] }))),
    );
    const user = userEvent.setup();
    render(<SuggestPanel clinic="c1" day={DAY} cells={monCells(() => 0.3)} />);
    await user.click(screen.getByRole("button", { name: /suggest changes/i }));
    expect(await screen.findByText(/No better moves found/i)).toBeInTheDocument();
  });

  it("Preview runs POST /whatif and shows a delta equal to after - before", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: 100 }),
        fc.integer({ min: 0, max: 100 }),
        async (beforePct, afterPct) => {
          cleanup();
          vi.unstubAllGlobals();
          const before = beforePct / 100;
          const after = afterPct / 100;
          const toHour = 17;
          // Current cells: source block mon-09 has `before`.
          const cells = monCells((h) => (h === 9 ? before : 0.3));
          let whatifCount = 0;
          vi.stubGlobal(
            "fetch",
            vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
              const url = String(input);
              const method = (init?.method ?? "GET").toUpperCase();
              if (url.includes("/suggest")) {
                return jsonResponse(suggestResponse());
              }
              if (url.includes("/whatif") && method === "POST") {
                whatifCount += 1;
                // moved block mon-17 now has `after`.
                const movedKey = blockKey(DAY, toHour);
                const next = HOURS.map((hour) => {
                  const share = blockKey(DAY, hour) === movedKey ? after : 0.3;
                  const reached = Math.round(share * 100);
                  return { day: DAY, hour, share: reached / 100, n: 100, reached };
                });
                return jsonResponse({
                  cells: next,
                  equity: {
                    ej: { share: 0.5, n: 10 },
                    lep: { share: 0.5, n: 10 },
                    age65: { share: 0.5, n: 10 },
                    zero_veh: { share: 0.5, n: 10 },
                  },
                  sources: [{ name: "GTFS", vintage: "2024" }],
                });
              }
              return jsonResponse({ detail: "nf" }, 404);
            }),
          );
          const user = userEvent.setup();
          render(<SuggestPanel clinic="c1" day={DAY} cells={cells} />);
          await user.click(screen.getByRole("button", { name: /suggest changes/i }));
          const previewBtn = await screen.findByRole("button", {
            name: /preview this move/i,
          });
          await user.click(previewBtn);
          const expected = `${deltaPts(before, after)} pts`;
          await waitFor(() => {
            expect(whatifCount).toBe(1);
            expect(
              screen.getByText(new RegExp(expected.replace("+", "\\+"))),
            ).toBeInTheDocument();
          });
          // sanity: before/after rendered as whole-percent
          expect(screen.getAllByText(new RegExp(pct(before))).length).toBeGreaterThan(0);
        },
      ),
      { numRuns: 15 },
    );
  });
});
