import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { PlanBarriers } from "../api/types";

/** The six barrier questions, in order, keyed to barrier_questions.yaml `maps_to`.
 * Question/answer text comes from i18n `planner.barrier.*` (UP-2.2). */
const STEPS = [
  "transport",
  "work_shift",
  "childcare",
  "escort",
  "cost",
  "language",
] as const;
type Step = (typeof STEPS)[number];

interface Draft {
  has_transport: boolean | null;
  work_shift: [number, number] | null;
  work_shift_on: boolean;
  childcare: boolean;
  childcare_window: [number, number] | null;
  cost_worry: boolean | null;
  has_escort: boolean | null;
  language: string;
}

function emptyDraft(lang: string): Draft {
  return {
    has_transport: null,
    work_shift: null,
    work_shift_on: false,
    childcare: false,
    childcare_window: null,
    cost_worry: null,
    has_escort: null,
    language: lang,
  };
}

/** Hours 0..24 as options for a window picker. */
const HOURS = Array.from({ length: 25 }, (_, h) => h);

export function BarrierCheck({
  lang,
  onSubmit,
  onBack,
}: {
  lang: string;
  onSubmit: (barriers: PlanBarriers) => void;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const [i, setI] = useState(0);
  const [d, setD] = useState<Draft>(() => emptyDraft(lang));
  const step: Step = STEPS[i];

  const set = (patch: Partial<Draft>) => setD((prev) => ({ ...prev, ...patch }));

  const back = () => (i === 0 ? onBack() : setI((n) => n - 1));
  const next = () => setI((n) => Math.min(n + 1, STEPS.length - 1));
  const isLast = i === STEPS.length - 1;

  const submit = () => {
    const barriers: PlanBarriers = {
      has_transport: d.has_transport ?? false,
      work_shift: d.work_shift_on ? d.work_shift ?? [9, 17] : null,
      childcare: d.childcare,
      childcare_window: d.childcare ? d.childcare_window : null,
      has_escort: d.has_escort ?? false,
      cost_worry: d.cost_worry ?? false,
      language: d.language,
    };
    onSubmit(barriers);
  };

  // A yes/no step is answerable only once the boolean is set.
  const canAdvance = (): boolean => {
    switch (step) {
      case "transport":
        return d.has_transport !== null;
      case "escort":
        return d.has_escort !== null;
      case "cost":
        return d.cost_worry !== null;
      default:
        return true; // window + language steps always have a valid default
    }
  };

  const YesNo = ({
    value,
    onChange,
    name,
  }: {
    value: boolean | null;
    onChange: (v: boolean) => void;
    name: string;
  }) => (
    <div className="yesno" role="group" aria-label={t("planner.barrier.yes") + " / " + t("planner.barrier.no")}>
      <button
        type="button"
        className="tap"
        aria-pressed={value === true}
        onClick={() => onChange(true)}
        data-testid={`${name}-yes`}
      >
        {t("planner.barrier.yes")}
      </button>
      <button
        type="button"
        className="tap"
        aria-pressed={value === false}
        onClick={() => onChange(false)}
        data-testid={`${name}-no`}
      >
        {t("planner.barrier.no")}
      </button>
    </div>
  );

  const WindowPicker = ({
    kind,
    value,
    onChange,
  }: {
    kind: "work_shift" | "childcare";
    value: [number, number] | null;
    onChange: (v: [number, number]) => void;
  }) => {
    const [s, e] = value ?? [9, 17];
    return (
      <div className="window-picker">
        <label>
          {t(`planner.barrier.${kind}.start`)}
          <select
            value={s}
            onChange={(ev) => onChange([Number(ev.target.value), e])}
            data-testid={`${kind}-start`}
          >
            {HOURS.map((h) => (
              <option key={h} value={h}>
                {String(h).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </label>
        <label>
          {t(`planner.barrier.${kind}.end`)}
          <select
            value={e}
            onChange={(ev) => onChange([s, Number(ev.target.value)])}
            data-testid={`${kind}-end`}
          >
            {HOURS.map((h) => (
              <option key={h} value={h}>
                {String(h).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </label>
      </div>
    );
  };

  return (
    <section aria-labelledby="barrier-title">
      <h2 id="barrier-title">{t("planner.barrier.title")}</h2>
      <p className="text-muted">
        {t("planner.step", { n: i + 1, total: STEPS.length })}
      </p>

      <fieldset className="barrier-step">
        <legend>{t(`planner.barrier.${step}.q`)}</legend>

        {step === "transport" && (
          <YesNo
            name="transport"
            value={d.has_transport}
            onChange={(v) => set({ has_transport: v })}
          />
        )}

        {step === "work_shift" && (
          <div className="window-step">
            <div className="yesno" role="group" aria-label={t("planner.barrier.work_shift.q")}>
              <button
                type="button"
                className="tap"
                aria-pressed={!d.work_shift_on}
                onClick={() => set({ work_shift_on: false })}
                data-testid="work_shift-none"
              >
                {t("planner.barrier.work_shift.none")}
              </button>
              <button
                type="button"
                className="tap"
                aria-pressed={d.work_shift_on}
                onClick={() => set({ work_shift_on: true, work_shift: d.work_shift ?? [7, 15] })}
                data-testid="work_shift-has"
              >
                {t("planner.barrier.work_shift.has")}
              </button>
            </div>
            {d.work_shift_on && (
              <WindowPicker
                kind="work_shift"
                value={d.work_shift}
                onChange={(v) => set({ work_shift: v })}
              />
            )}
          </div>
        )}

        {step === "childcare" && (
          <div className="window-step">
            <div className="yesno" role="group" aria-label={t("planner.barrier.childcare.q")}>
              <button
                type="button"
                className="tap"
                aria-pressed={!d.childcare}
                onClick={() => set({ childcare: false, childcare_window: null })}
                data-testid="childcare-none"
              >
                {t("planner.barrier.childcare.none")}
              </button>
              <button
                type="button"
                className="tap"
                aria-pressed={d.childcare}
                onClick={() => set({ childcare: true, childcare_window: d.childcare_window ?? [15, 18] })}
                data-testid="childcare-has"
              >
                {t("planner.barrier.childcare.has")}
              </button>
            </div>
            {d.childcare && (
              <>
                <p className="text-muted">{t("planner.barrier.childcare.help")}</p>
                <WindowPicker
                  kind="childcare"
                  value={d.childcare_window}
                  onChange={(v) => set({ childcare_window: v })}
                />
              </>
            )}
          </div>
        )}

        {step === "escort" && (
          <>
            <YesNo
              name="escort"
              value={d.has_escort}
              onChange={(v) => set({ has_escort: v })}
            />
            <p className="text-muted">{t("planner.barrier.escort.help")}</p>
          </>
        )}

        {step === "cost" && (
          <YesNo
            name="cost"
            value={d.cost_worry}
            onChange={(v) => set({ cost_worry: v })}
          />
        )}

        {step === "language" && (
          <div className="yesno" role="group" aria-label={t("planner.barrier.language.q")}>
            <button
              type="button"
              className="tap"
              aria-pressed={d.language === "en"}
              onClick={() => set({ language: "en" })}
              data-testid="language-en"
            >
              {t("planner.barrier.language.en")}
            </button>
            <button
              type="button"
              className="tap"
              aria-pressed={d.language === "es"}
              onClick={() => set({ language: "es" })}
              data-testid="language-es"
            >
              {t("planner.barrier.language.es")}
            </button>
          </div>
        )}
      </fieldset>

      <div className="barrier-nav">
        <button type="button" className="btn-secondary" onClick={back}>
          {t("planner.barrier.back")}
        </button>
        {isLast ? (
          <button
            type="button"
            className="btn-primary"
            onClick={submit}
            disabled={!canAdvance()}
            data-testid="barrier-submit"
          >
            {t("planner.barrier.submit")}
          </button>
        ) : (
          <button
            type="button"
            className="btn-primary"
            onClick={next}
            disabled={!canAdvance()}
            data-testid="barrier-next"
          >
            {t("planner.barrier.next")}
          </button>
        )}
      </div>
    </section>
  );
}
