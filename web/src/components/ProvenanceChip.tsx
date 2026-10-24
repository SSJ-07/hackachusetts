import { useRef } from "react";
import type { SourceRef } from "../api/types";
import { useTranslation } from "react-i18next";
import { useProvenance } from "./provenance-context";

/**
 * Shows a number's provenance (ui-style.md: every on-screen number shows its
 * source, vintage and link). Renders inline next to the number.
 *
 * When a `provId` is given AND a ProvenanceContext handler is in scope, the chip
 * renders as a button that opens the "How we know this is right" drawer
 * (ui-planner UP-6). Otherwise it keeps the plain link/label behaviour.
 */
export function ProvenanceChip({
  source,
  provId,
}: {
  source: SourceRef;
  provId?: string;
}) {
  const { t } = useTranslation();
  const openProvenance = useProvenance();
  const btnRef = useRef<HTMLButtonElement | null>(null);
  const label = `${source.name} (${t("sources.vintage")} ${source.vintage})`;

  if (provId && openProvenance) {
    return (
      <button
        type="button"
        ref={btnRef}
        className="chip chip-button"
        onClick={() => openProvenance(provId, btnRef.current)}
        aria-haspopup="dialog"
      >
        <span aria-hidden="true" className="chip-icon">
          ⓘ
        </span>
        {label}
        <span className="visually-hidden"> — {t("planner.provenance.open")}</span>
      </button>
    );
  }

  return (
    <span className="chip">
      {source.url ? (
        <a href={source.url} target="_blank" rel="noreferrer">
          {label}
        </a>
      ) : (
        <span>{label}</span>
      )}
    </span>
  );
}
