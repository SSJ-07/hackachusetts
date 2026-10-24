import { defineConfig, devices } from "@playwright/test";

// Read env without pulling in @types/node (matches vite.config.ts).
const ENV = (globalThis as { process?: { env?: Record<string, string | undefined> } })
  .process?.env;
const CI = !!ENV?.CI;

/**
 * Playwright config for the web UI e2e + accessibility suites.
 *
 * - Chromium only (the demo targets one evergreen browser).
 * - webServer boots the real Vite dev server on 127.0.0.1:5173. We point the API
 *   client at the same-origin "/api" prefix (VITE_API_BASE=/api) so every data
 *   request is same-origin and can be intercepted with page.route — no backend
 *   needs to run for e2e.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: CI,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !CI,
    timeout: 120_000,
    env: {
      // Make the app call the same-origin /api prefix so page.route can stub it.
      VITE_API_BASE: "/api",
    },
  },
});
