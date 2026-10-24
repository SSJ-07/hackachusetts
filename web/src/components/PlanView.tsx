import { useTranslation } from "react-i18next";
import type { PlanLeg, PlanResponse, OptionKind } from "../api/types";
import { ProvenanceChip } from "./ProvenanceChip";

/** Seconds since local midnight -> "HH:MM" clock time. GTFS times may exceed
 * 86400 (past midnight); we show the wall-clock hour with mod, never wrapping
 * the stored seconds (contracts.md convention). */
function clock(sec: number): string {
  const m = Math.floor((sec % 86400) / 60);
  const hh = String(Math.floor(m / 60)).padStart(2, "0");
  const mm = String(m % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}

/** A per-option icon/shape so meaning is never colour-only (UP-P4). */
const KIND_ICON: Record<OptionKind, string> = {
  slot: "🚌",
  ride: "🚐",
  tele: "📞",
  prep: "📄",
  none: "🧭",
};

function Leg({ leg }: { leg: PlanLeg }) {
  const { t } = useTranslation();
  const mode =
    leg.kind === "bus"
      ? t("planner.itinerary.bus", { route: leg.route_id ?? "" })
      : t("planner.itinerary.walk");
  return (
    <li className="leg">
      <span className="leg-mode">{mode}</span>{" "}
      <span className="leg-detail">
        {t("planner.itinerary.from", { stop: leg.from_stop })}{" "}
        {t("planner.itinerary.to", { stop: leg.to_stop })}{" "}
        {t("planner.itinerary.at", { time: clock(leg.dep) })}
      </span>
    </li>
  );
}

export function PlanView({ plan }: { plan: PlanResponse }) {
  const { t } = useTranslation();
  const it = plan.itinerary;
  const hasItinerary = it.out_legs.length > 0 || it.ret_legs.length > 0;
  const pt1Entries = Object.entries(plan.pt1_prefill ?? {});

  return (
    <section aria-labelledby="plan-heading" className="plan-view">
      <h2 id="plan-heading">{t("planner.plan.heading")}</h2>

      <ol className="option-list">
        {plan.options.map((o, idx) => {
          const rec =
            (o.details?.recurrence as { per_week?: number } | undefined) ?? null;
          return (
            <li key={`${o.kind}-${idx}`} className={`option option-${o.kind}`}>
              <div className="option-head">
                <span aria-hidden="true" className="option-icon">
                  {KIND_ICON[o.kind]}
                </span>
                <span className="option-kind">
                  {t(`planner.plan.optionKinds.${o.kind}`)}
                </span>
                {idx === 0 && o.kind !== "none" && (
                  <span className="badge">{t("planner.plan.recommended")}</span>
                )}
              </div>
              <p className="option-why">
                <span className="option-why-label">
                  {t("planner.plan.whichReason")}:
                </span>{" "}
                {o.why}
              </p>
              {rec?.per_week != null && (
                <p className="option-recurrence">
                  {t("planner.plan.recurrence", { count: rec.per_week })}
                </p>
              )}
            </li>
          );
        })}
      </ol>

      {/* Itinerary */}
      <section aria-labelledby="itin-heading" className="itinerary">
        <h3 id="itin-heading">{t("planner.itinerary.title")}</h3>
        {hasItinerary ? (
          <div className="itin-cols">
            <div>
              <h4>{t("planner.itinerary.out")}</h4>
              <ol className="legs">
                {it.out_legs.map((leg, k) => (
                  <Leg key={`out-${k}`} leg={leg} />
                ))}
              </ol>
            </div>
            <div>
              <h4>{t("planner.itinerary.ret")}</h4>
              <ol className="legs">
                {it.ret_legs.map((leg, k) => (
                  <Leg key={`ret-${k}`} leg={leg} />
                ))}
              </ol>
              {it.last_bus_home != null && (
                <p className="last-bus">
                  {t("planner.itinerary.lastBus", {
                    time: clock(it.last_bus_home),
                  })}
                </p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-muted">{t("planner.itinerary.none")}</p>
        )}
        {/* plan_b renders ONLY when the API supplies it (reviewed templates, M3). */}
        {it.plan_b && <p className="plan-b">{it.plan_b}</p>}
      </section>

      {/* Phone-sized preview */}
      <section aria-labelledby="phone-heading" className="phone-preview-wrap">
        <h3 id="phone-heading">{t("planner.phone.title")}</h3>
        <p className="text-muted">{t("planner.phone.help")}</p>
        <div className="phone-frame" data-testid="phone-preview">
          <div className="phone-screen">
            <p className="phone-title">
              {t(`planner.plan.optionKinds.${plan.options[0]?.kind ?? "none"}`)}
            </p>
            {hasItinerary ? (
              <ol className="phone-legs">
                {[...it.out_legs, ...it.ret_legs].map((leg, k) => (
                  <li key={`p-${k}`}>
                    {leg.kind === "bus"
                      ? t("planner.itinerary.bus", { route: leg.route_id ?? "" })
                      : t("planner.itinerary.walk")}{" "}
                    {clock(leg.dep)}
                  </li>
                ))}
              </ol>
            ) : (
              <p>{t("planner.itinerary.none")}</p>
            )}
          </div>
        </div>
      </section>

      {/* PT-1 pre-fill summary */}
      <section aria-labelledby="pt1-heading" className="pt1-summary">
        <h3 id="pt1-heading">{t("planner.pt1.title")}</h3>
        <p className="text-muted">{t("planner.pt1.note")}</p>
        {pt1Entries.length > 0 ? (
          <dl className="pt1-list">
            {pt1Entries.map(([k, v]) => (
              <div key={k} className="pt1-row">
                <dt>{k}</dt>
                <dd>
                  {v == null || v === "" ? (
                    <em className="pt1-todo">{t("planner.pt1.toComplete")}</em>
                  ) : (
                    String(v)
                  )}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-muted">{t("planner.pt1.empty")}</p>
        )}
      </section>

      {/* Provenance: the plan's reachability rests on the router's round-trip
          rule. The chip opens the drawer (RT-8 from the raptor-router spec). */}
      <ProvenanceChip
        source={{ name: "PVTA GTFS", vintage: "2026-09-18" }}
        provId="RT-8"
      />
    </section>
  );
}
