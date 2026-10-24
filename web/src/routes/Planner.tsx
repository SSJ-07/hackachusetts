import { useTranslation } from "react-i18next";

/** Placeholder — the Visit Planner is owned by M4. */
export function Planner() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t("planner.title")}</h1>
      <p className="notice" role="note">
        {t("planner.placeholder")}
      </p>
    </>
  );
}
