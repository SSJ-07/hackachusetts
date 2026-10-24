import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import es from "./es.json";

export const SUPPORTED = ["en", "es"] as const;
export type Lang = (typeof SUPPORTED)[number];

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnNull: false,
});

/** Set <html lang> and the i18next language together. */
export function setLanguage(lang: Lang): void {
  void i18n.changeLanguage(lang);
  if (typeof document !== "undefined") {
    document.documentElement.lang = lang;
  }
}

export default i18n;
