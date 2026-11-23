"use client";

import Link from "next/link";
import { useState } from "react";
import { Clapperboard, Menu, Search, X } from "lucide-react";
import { LanguageSwitcher, useI18n } from "./i18n-provider";

const links = [
  ["nav.home", "/"],
  ["nav.movies", "/movies"],
  ["nav.kids", "/kids"],
  ["nav.series", "/series"],
  ["nav.african", "/categories/african-cinema"],
  ["nav.anime", "/categories/anime"],
  ["nav.animation", "/categories/animated-movies"],
  ["nav.documentaries", "/categories/documentaries"],
  ["nav.categories", "/categories"],
] as const;

export function SiteHeader() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#100e0c]/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-wide">
          <Clapperboard className="h-6 w-6 text-amber" aria-hidden />
          <span>
            SOSPANA <span className="text-amber">CINEMA</span>
          </span>
        </Link>
        <nav className="ml-4 hidden items-center gap-4 text-sm text-ink/80 lg:flex" aria-label="Primary">
          {links.map(([key, href]) => (
            <Link key={key} href={href} className="hover:text-amber">
              {t(key)}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher />
          <Link href="/search" aria-label={t("nav.search")} className="rounded-full p-2 hover:bg-white/10">
            <Search className="h-5 w-5" />
          </Link>
          <button type="button" className="rounded-full p-2 lg:hidden" aria-expanded={open} aria-label="Menu" onClick={() => setOpen((value) => !value)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {open ? (
        <nav className="space-y-1 border-t border-white/10 px-4 py-3 lg:hidden" aria-label="Mobile">
          {links.map(([key, href]) => (
            <Link key={key} href={href} className="block rounded-xl px-2 py-2 hover:bg-white/5" onClick={() => setOpen(false)}>
              {t(key)}
            </Link>
          ))}
          <Link href="/search" className="block rounded-xl px-2 py-2 hover:bg-white/5" onClick={() => setOpen(false)}>
            {t("nav.search")}
          </Link>
        </nav>
      ) : null}
    </header>
  );
}

export function DemoBanner({ warning }: { warning: string | null }) {
  const { t } = useI18n();
  return (
    <div className="border-b border-amber/30 bg-amber/10">
      <p className="mx-auto max-w-6xl px-4 py-2 text-sm text-amber">{t("banner")}</p>
      {warning ? <p className="mx-auto max-w-6xl px-4 pb-2 text-sm text-coral">{warning}</p> : null}
    </div>
  );
}

export function SiteFooter() {
  const { t } = useI18n();
  return (
    <footer className="mt-16 border-t border-white/10">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-3">
        <div>
          <p className="font-display text-xl">SOSPANA CINEMA</p>
          <p className="mt-2 text-sm text-ink/70">Free Entertainment. Everywhere.</p>
        </div>
        <div className="flex flex-col gap-2 text-sm">
          <Link href="/categories/south-african-movies">South African Movies</Link>
          <Link href="/categories/classic-cinema">Classic Cinema</Link>
          <Link href="/categories/educational-movies">Educational</Link>
          <Link href="/categories/family-entertainment">Family</Link>
          <Link href="/kids">Kids Cinema</Link>
        </div>
        <div className="flex flex-col gap-2 text-sm">
          <Link href="/library">{t("footer.device")}</Link>
          <Link href="/takedown">{t("footer.takedown")}</Link>
          <Link href="/privacy">{t("footer.privacy")}</Link>
          <Link href="/terms">{t("footer.terms")}</Link>
          <Link href="/admin">Admin</Link>
        </div>
      </div>
      <p className="mx-auto max-w-6xl px-4 pb-8 text-xs text-ink/50">
        Film metadata in this demonstration comes from the source record named on each title. TMDB is used only when TMDB_API_KEY is set. Sospana Cinema is not endorsed or certified by TMDB. This catalogue is not a claim of zero legal risk.
      </p>
    </footer>
  );
}
