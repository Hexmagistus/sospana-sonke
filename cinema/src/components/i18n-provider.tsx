"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { LOCALES, translate, type Locale, type MessageKey } from "@/lib/i18n";

const KEY = "sospana-cinema-locale";

const I18nContext = createContext<{
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}>({
  locale: "en",
  setLocale: () => undefined,
  t: (key) => translate("en", key),
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem(KEY);
    if (saved === "en" || saved === "af" || saved === "fr") setLocaleState(saved);
  }, []);

  const value = useMemo(
    () => ({
      locale,
      setLocale: (next: Locale) => {
        setLocaleState(next);
        window.localStorage.setItem(KEY, next);
        document.documentElement.lang = next === "af" ? "af" : next === "fr" ? "fr" : "en";
      },
      t: (key: MessageKey) => translate(locale, key),
    }),
    [locale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <label className="flex items-center gap-2 text-xs text-ink/70">
      <span className="sr-only">Language</span>
      <select
        aria-label="Language"
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        className="rounded-full border border-white/15 bg-black/30 px-2 py-1 text-ink"
      >
        {LOCALES.map((item) => (
          <option key={item} value={item}>
            {item === "en" ? "English" : item === "af" ? "Afrikaans" : "Français"}
          </option>
        ))}
      </select>
    </label>
  );
}
