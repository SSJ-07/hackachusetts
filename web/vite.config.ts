/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The browser only talks to OUR API (ui-style.md). /api -> FastAPI on localhost.
// Read the dev proxy target from the environment without pulling in @types/node.
const env = (globalThis as { process?: { env?: Record<string, string | undefined> } })
  .process?.env;
const API = env?.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: API, changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
