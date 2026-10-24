import type { SourceRef } from "../api/types";
import { useTranslation } from "react-i18next";

/** Lists every source + vintage behind the numbers on screen. The guardrail is
 * that no number appears without a source; this footer is the audit trail. */
export function SourcesFooter({ sources }: { sources: SourceRef[] }) {
  const { t } = useTranslation();
  return (
    <footer className="sources" aria-labelledby="sources-h">
      <h2 id="sources-h">{t("sources.title")}</h2>
      <p>{t("sources.intro")}</p>
      <ul>
        {sources.map((s, i) => (
          <li key={`${s.name}-${s.vintage}-${i}`}>
            {s.url ? (
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.name}
              </a>
            ) : (
              <span>{s.name}</span>
            )}{" "}
            — {t("sources.vintage")} {s.vintage}
          </li>
        ))}
      </ul>
    </footer>
  );
}
