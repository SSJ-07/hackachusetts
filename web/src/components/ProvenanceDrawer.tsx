import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, getProvenance } from "../api/client";
import type { ProvenanceResponse } from "../api/types";

type Load =
  | { kind: "loading" }
  | { kind: "notfound" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: ProvenanceResponse };

/**
 * "How we know this is right" drawer (ui-planner UP-6). Opened by a
 * ProvenanceChip; fetches GET /provenance?id and shows
 * source -> vintage -> requirement -> properties -> status -> spec link.
 *
 * - role="dialog" aria-modal; closes on the Close button and on Escape.
 * - restores focus to the chip that opened it (restoreFocusTo).
 * - status is shown as text + shape, never colour alone (accessibility.md).
 */
export function ProvenanceDrawer({
  id,
  restoreFocusTo,
  onClose,
}: {
  id: string;
  restoreFocusTo: HTMLElement | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    setLoad({ kind: "loading" });
    getProvenance(id, ac.signal)
      .then((data) => setLoad({ kind: "ready", data }))
      .catch((err: unknown) => {
        if (ac.signal.aborted) return;
        if (err instanceof ApiError && err.status === 404) {
          setLoad({ kind: "notfound" });
          return;
        }
        setLoad({
          kind: "error",
          message: err instanceof ApiError ? err.message : String(err),
        });
      });
    return () => ac.abort();
  }, [id]);

  // Move focus into the drawer on open; restore it on close.
  useEffect(() => {
    closeRef.current?.focus();
    return () => restoreFocusTo?.focus();
  }, [restoreFocusTo]);

  // Esc closes; Tab is trapped within the panel.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const focusables = panel.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [onClose]);

  const statusText = (s: "pass" | "fail" | "pending") =>
    t(`planner.provenance.status.${s}`);
  const statusShape = (s: "pass" | "fail" | "pending") =>
    s === "pass" ? "✓" : s === "fail" ? "✗" : "…";

  return (
    <div className="drawer-scrim" onClick={onClose} data-testid="provenance-scrim">
      <div
        ref={panelRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={t("planner.provenance.title")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-head">
          <h2>{t("planner.provenance.title")}</h2>
          <button
            type="button"
            ref={closeRef}
            className="drawer-close"
            onClick={onClose}
          >
            {t("planner.provenance.close")}
          </button>
        </div>

        {load.kind === "loading" && (
          <p role="status">{t("planner.provenance.loading")}</p>
        )}
        {load.kind === "notfound" && (
          <p role="status">{t("planner.provenance.notFound")}</p>
        )}
        {load.kind === "error" && (
          <p role="alert">{load.message}</p>
        )}

        {load.kind === "ready" && (
          <dl className="prov-list">
            <dt>{t("planner.provenance.source")}</dt>
            <dd>{load.data.source.name}</dd>
            <dt>{t("planner.provenance.vintage")}</dt>
            <dd>{load.data.source.vintage}</dd>
            <dt>{t("planner.provenance.requirement")}</dt>
            <dd>{load.data.requirement_id}</dd>
            <dt>{t("planner.provenance.properties")}</dt>
            <dd>
              <ul className="prov-props">
                {load.data.properties.map((p) => (
                  <li key={p.name} className={`prov-prop prov-${p.status}`}>
                    <span aria-hidden="true" className="prov-shape">
                      {statusShape(p.status)}
                    </span>
                    <span>{p.name}</span>
                    <span className="prov-status-text">
                      {" — "}
                      {statusText(p.status)}
                    </span>
                  </li>
                ))}
              </ul>
            </dd>
            <dt>{t("planner.provenance.specLink")}</dt>
            <dd>
              <code className="prov-spec">{load.data.spec_link}</code>
            </dd>
          </dl>
        )}
      </div>
    </div>
  );
}
