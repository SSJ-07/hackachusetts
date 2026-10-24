import { useTranslation } from "react-i18next";
import { useHashRoute } from "./lib/router";
import type { Route } from "./lib/router";
import { SUPPORTED, setLanguage } from "./i18n";
import type { Lang } from "./i18n";
import { Audit } from "./routes/Audit";
import { Planner } from "./routes/Planner";
import { About } from "./routes/About";

function NavLink({ to, route, label }: { to: Route; route: Route; label: string }) {
  return (
    <a href={`#${to}`} aria-current={route === to ? "page" : undefined}>
      {label}
    </a>
  );
}

export default function App() {
  const { t, i18n } = useTranslation();
  const route = useHashRoute();
  const current = (i18n.resolvedLanguage ?? "en") as Lang;

  return (
    <>
      <a className="skip-link" href="#main">
        {t("app.skipToContent")}
      </a>
      <header className="app-header">
        <span className="brand">{t("app.brand")}</span>
        <nav className="app-nav" aria-label={t("app.brand")}>
          <NavLink to="/audit" route={route} label={t("app.nav.audit")} />
          <NavLink to="/planner" route={route} label={t("app.nav.planner")} />
          <NavLink to="/about" route={route} label={t("app.nav.about")} />
        </nav>
        <div className="lang-switch" role="group" aria-label={t("app.language")}>
          {SUPPORTED.map((lng) => (
            <button
              key={lng}
              type="button"
              aria-pressed={current === lng}
              onClick={() => setLanguage(lng)}
            >
              {lng.toUpperCase()}
            </button>
          ))}
        </div>
      </header>
      <main className="app-main" id="main">
        {route === "/audit" && <Audit />}
        {route === "/planner" && <Planner />}
        {route === "/about" && <About />}
      </main>
    </>
  );
}
