import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import catalog from "./catalog.json";

export type Lang = "en" | "th";

const LANG_KEY = "metro_cart_ui_lang";
const SUPPORTED: Lang[] = ["en", "th"];

type Catalog = Record<string, { en: string; th: string }>;

const TRANSLATIONS = catalog as Catalog;

function readLang(): Lang {
  try {
    const stored = localStorage.getItem(LANG_KEY) as Lang | null;
    return stored && SUPPORTED.includes(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

function translate(lang: Lang, key: string, params?: Record<string, string | number>) {
  const entry = TRANSLATIONS[key];
  if (!entry) return key;
  let text = entry[lang] || entry.en || key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replaceAll(`{${k}}`, String(v ?? ""));
    }
  }
  return text;
}

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => readLang());

  const setLang = useCallback((next: Lang) => {
    const value = SUPPORTED.includes(next) ? next : "en";
    localStorage.setItem(LANG_KEY, value);
    document.documentElement.lang = value === "th" ? "th" : "en";
    setLangState(value);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => translate(lang, key, params),
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function LanguageToggle({ className = "" }: { className?: string }) {
  const { lang, setLang, t } = useI18n();
  return (
    <label className={`inline-flex items-center gap-2 text-sm text-muted ${className}`}>
      <span className="font-medium">{t("language")}</span>
      <select
        className="rounded-lg border border-border bg-white px-2 py-1.5 font-semibold text-slate-700"
        value={lang}
        aria-label={t("language")}
        onChange={(e) => setLang(e.target.value as Lang)}
      >
        <option value="en">{t("lang_english")}</option>
        <option value="th">{t("lang_thai")}</option>
      </select>
    </label>
  );
}

export const PAGE_LABEL_KEYS = {
  ADMIN_PANEL: "nav_admin_panel",
  FRAUD_DASHBOARD: "nav_fraud_dashboard",
  POWER_BI_DASHBOARD: "nav_power_bi",
  AI_CHATBOT: "nav_analytics_ai",
} as const;
