import { describe, expect, it } from "vitest";
import en from "./en.json";
import es from "./es.json";

/** Flatten nested JSON into dotted key paths. */
function keys(obj: unknown, prefix = ""): string[] {
  if (obj == null || typeof obj !== "object") return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    keys(v, prefix ? `${prefix}.${k}` : k),
  );
}

describe("i18n parity (ui-style.md)", () => {
  it("EN and ES have exactly the same keys", () => {
    const enKeys = keys(en).sort();
    const esKeys = keys(es).sort();
    const missingInEs = enKeys.filter((k) => !esKeys.includes(k));
    const missingInEn = esKeys.filter((k) => !enKeys.includes(k));
    expect({ missingInEs, missingInEn }).toEqual({
      missingInEs: [],
      missingInEn: [],
    });
  });
});
