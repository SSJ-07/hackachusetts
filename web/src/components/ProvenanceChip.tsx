import type { SourceRef } from "../api/types";
import { useTranslation } from "react-i18next";

/**
 * Shows a number's provenance (ui-style.md: every on-screen number shows its
 * source, vintage and link). Renders inline next to the number.
 */
export function ProvenanceChip({ source }: { source: SourceRef }) {
  const { t } = useTranslation();
  const label = `${source.name} (${t("sources.vintage")} ${source.vintage})`;
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
