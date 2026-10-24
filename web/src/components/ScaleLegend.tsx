import { useTranslation } from "react-i18next";

/** Numbered legend for the 5-step data scale. Pairs colour with a number range
 * so meaning is never colour-only (accessibility.md 1.4.1). */
export function ScaleLegend() {
  const { t } = useTranslation();
  const ranges = [
    { step: 0, label: "0–20%" },
    { step: 1, label: "20–40%" },
    { step: 2, label: "40–60%" },
    { step: 3, label: "60–80%" },
    { step: 4, label: "80–100%" },
  ];
  return (
    <div className="legend" role="group" aria-label={t("legend.title")}>
      <span className="visually-hidden">{t("legend.title")}</span>
      {ranges.map((r) => (
        <span className="swatch" key={r.step}>
          <span
            className="box"
            style={{ background: `var(--scale-${r.step})` }}
            aria-hidden="true"
          />
          <span>{r.label}</span>
        </span>
      ))}
      <span className="swatch">
        <span
          className="box"
          style={{ background: "var(--scale-na)" }}
          aria-hidden="true"
        />
        <span>{t("legend.none")}</span>
      </span>
    </div>
  );
}
