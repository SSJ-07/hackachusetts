import type { Page, Route } from "@playwright/test";

/**
 * Deterministic fixtures for the Audit screen e2e. Served via page.route so no
 * backend runs: the app is pointed at the same-origin "/api" prefix (see
 * playwright.config webServer env), and these handlers answer every request.
 *
 * Numbers are made up but internally consistent (reached = round(share * n)) and
 * every payload carries sources, as the real API does.
 */

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
const HOURS = Array.from({ length: 12 }, (_, i) => i + 7); // 07..18

const SOURCES = [
  { name: "ACS 5-year", vintage: "2022" },
  { name: "GTFS feed", vintage: "2024" },
];

type Cell = {
  day: string;
  hour: number;
  share: number;
  n: number;
  reached: number;
};

function cell(day: string, hour: number, share: number): Cell {
  const n = 100;
  const s = Math.max(0, Math.min(1, share));
  const reached = Math.round(s * n);
  return { day, hour, share: reached / n, n, reached };
}

/** A fixed, reproducible grid: share rises across the day, differs per weekday. */
export function auditGrid(): Cell[] {
  const cells: Cell[] = [];
  DAYS.forEach((day, di) => {
    HOURS.forEach((hour, hi) => {
      // 0.10 .. 0.85, deterministic.
      const share = 0.1 + ((di * 3 + hi * 7) % 16) / 20;
      cells.push(cell(day, hour, share));
    });
  });
  return cells;
}

export const AUDIT_RESPONSE = {
  cells: auditGrid(),
  equity: {
    ej: { share: 0.42, n: 1200 },
    lep: { share: 0.31, n: 540 },
    age65: { share: 0.58, n: 880 },
    zero_veh: { share: 0.37, n: 1500 },
  },
  sources: SOURCES,
};

export const CLINICS_RESPONSE = {
  clinics: [
    {
      clinic_id: "demo-1",
      clinic_name: "Riverside Community Health",
      visit_type: "primary care",
      visit_minutes: 30,
      stop_id: "stop-001",
      is_demo_anchor: true,
    },
    {
      clinic_id: "demo-2",
      clinic_name: "Northside Pediatrics",
      visit_type: "pediatrics",
      visit_minutes: 20,
      stop_id: "stop-002",
      is_demo_anchor: false,
    },
  ],
  sources: SOURCES,
};

export const BLOCKGROUPS_RESPONSE = {
  features: [
    {
      bg_geoid: "25017350100",
      lat: 42.37,
      lon: -71.1,
      carless_adults: 220,
      share: 0.44,
      desert: false,
    },
    {
      bg_geoid: "25017350200",
      lat: 42.38,
      lon: -71.09,
      carless_adults: 95,
      share: 0.0,
      desert: true,
    },
  ],
  sources: SOURCES,
};

/** What-if: echo the audit grid but bump the moved block's share to a fixed value. */
export function whatIfResponse(block: string, to: number) {
  const day = block.slice(0, 3);
  const cells = auditGrid().map((c) =>
    c.day === day && c.hour === to ? cell(c.day, c.hour, 0.9) : c,
  );
  return { cells, equity: AUDIT_RESPONSE.equity, sources: SOURCES };
}

export const SUGGEST_RESPONSE = {
  clinic: "demo-1",
  day: "mon",
  k: 3,
  baseline_score: 12.4,
  suggested_score: 15.1,
  baseline_blocks: [7, 8, 9],
  suggested_blocks: [7, 8, 17],
  open_hours: [17, 18],
  changes: [
    {
      change: { kind: "move_block", day: "mon", block: "mon-09", to: 17 },
      gain_visit_hours: 3.5,
      gain_people: 14,
      sources: SOURCES,
    },
    {
      change: { kind: "move_block", day: "mon", block: "mon-08", to: 18 },
      gain_visit_hours: 2.0,
      gain_people: 8,
      sources: [
        ...SOURCES,
        { name: "Modeled estimate", vintage: "n/a", illustrative: true },
      ],
    },
  ],
  sources: SOURCES,
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

/**
 * Install all /api route handlers on a page. The app calls /api/* same-origin
 * (VITE_API_BASE=/api), so one glob covers them; we branch on the path.
 *
 * @param suggestStatus 200 serves SUGGEST_RESPONSE; 503 serves the mock-mode
 *   "needs real data" body for the a11y/empty-state checks.
 */
export async function mockApi(
  page: Page,
  opts: { suggestStatus?: number } = {},
): Promise<void> {
  const suggestStatus = opts.suggestStatus ?? 200;
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^\/api/, "");
      const method = route.request().method();

      if (path === "/clinics") return json(route, CLINICS_RESPONSE);
      if (path === "/audit/blockgroups") return json(route, BLOCKGROUPS_RESPONSE);
      if (path === "/audit") return json(route, AUDIT_RESPONSE);
      if (path === "/whatif" && method === "POST") {
        const body = route.request().postDataJSON() as {
          shift: { block: string; to: number };
        };
        return json(route, whatIfResponse(body.shift.block, body.shift.to));
      }
      if (path === "/suggest") {
        if (suggestStatus === 503) {
          return json(
            route,
            { detail: "Schedule suggestions need the real cube." },
            503,
          );
        }
        return json(route, SUGGEST_RESPONSE);
      }
      return json(route, { detail: "not found" }, 404);
    },
  );
}
