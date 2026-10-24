import type { Equity } from "../api/types";
import { pct } from "../lib/scale";
import { useTranslation } from "react-i18next";

const ORDER = ["ej", "lep", "age65", "zero_veh"] as const;

/** EquityPanel — EJ / limited-English / 65+ / zero-vehicle reach split. */
export function EquityPanel({ equity }: { equity: Equity }) {
  const { t } = useTranslation();
  return (
    <section className="panel" aria-labelledby="equity-h">
      <h2 id="equity-h">{t("equity.title")}</h2>
      <dl>
        {ORDER.map((key) => {
          const g = equity[key];
          return (
            <div className="equity-row" key={key}>
              <dt>{t(`equity.groups.${key}`)}</dt>
              <dd>
                <strong>{pct(g.share)}</strong>{" "}
                <span className="text-muted">{t("equity.ofN", { n: g.n })}</span>
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
