import { scaleLinear } from "d3-scale";
import type { AuditCell, Day } from "../api/types";
import { HOURS, cellVars, hourLabel, pct } from "../lib/scale";
import { useTranslation } from "react-i18next";

/**
 * DayRibbon — one day's 12 hour blocks on a timeline. D3 computes the scales;
 * React renders the SVG (ui-style.md: D3 only for scales, never touches the DOM).
 * Shown as a real data table alternative via an aria-label on each bar.
 */
export function DayRibbon({
  day,
  cells,
}: {
  day: Day | null;
  cells: AuditCell[];
}) {
  const { t } = useTranslation();
  if (!day) {
    return (
      <section className="panel" aria-labelledby="ribbon-h">
        <h2 id="ribbon-h">{t("audit.ribbon.empty")}</h2>
      </section>
    );
  }

  const dayName = t(`audit.days.${day}`);
  const byHour = new Map(cells.filter((c) => c.day === day).map((c) => [c.hour, c]));

  const W = 520;
  const H = 120;
  const padL = 8;
  const padR = 8;
  const padB = 22;
  const padT = 8;
  const bw = (W - padL - padR) / HOURS.length;
  const y = scaleLinear().domain([0, 1]).range([H - padB, padT]);

  return (
    <section className="panel" aria-labelledby="ribbon-h">
      <h2 id="ribbon-h">{t("audit.ribbon.title", { day: dayName })}</h2>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={t("audit.ribbon.title", { day: dayName })}
      >
        {HOURS.map((h, i) => {
          const c = byHour.get(h);
          const share = c ? c.share : null;
          const top = share == null ? H - padB : y(share);
          const vars = cellVars(share);
          const x = padL + i * bw;
          const name =
            c == null
              ? t("audit.cellNoData", { day: dayName, hour: hourLabel(h) })
              : t("audit.cellName", {
                  day: dayName,
                  hour: hourLabel(h),
                  pct: Math.round(c.share * 100),
                  n: c.n,
                });
          return (
            <g key={h}>
              <rect
                x={x + 1}
                y={top}
                width={bw - 2}
                height={Math.max(0, H - padB - top)}
                fill={vars["--cell-bg"]}
                stroke="var(--border)"
              >
                <title>{name}</title>
              </rect>
              {/* number printed above the bar — meaning is never colour-only */}
              {share != null && (
                <text
                  x={x + bw / 2}
                  y={Math.max(padT + 10, top - 3)}
                  textAnchor="middle"
                  fontSize="10"
                  fill="var(--text)"
                >
                  {pct(share)}
                </text>
              )}
              <text
                x={x + bw / 2}
                y={H - 6}
                textAnchor="middle"
                fontSize="9"
                fill="var(--text-muted)"
              >
                {h}
              </text>
            </g>
          );
        })}
      </svg>
      {/* Table alternative for screen readers (accessibility.md: chart has a table). */}
      <table className="visually-hidden">
        <caption>{t("audit.ribbon.title", { day: dayName })}</caption>
        <thead>
          <tr>
            <th scope="col">{t("audit.hour")}</th>
            <th scope="col">{t("equity.share")}</th>
          </tr>
        </thead>
        <tbody>
          {HOURS.map((h) => {
            const c = byHour.get(h);
            return (
              <tr key={h}>
                <th scope="row">{hourLabel(h)}</th>
                <td>{c ? `${pct(c.share)} (${c.reached}/${c.n})` : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
