"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Alert, Spinner, EmptyState } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { HowToUseCard } from "@/lib/explorer/HowToUseCard";
import { guideStepsFor } from "@/lib/directoryFilters";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import { CompanyActionsRow, NotCountedNotice, OpenVacancyCount, TrendingBadge, ShortlistStar } from "@/components/CompanyActions";
import { CompanyPreviewModal } from "@/components/CompanyPreviewModal";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { FunSpinner } from "@/components/FunSpinner";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";
import { CountryExplorer, type ExplorerStats } from "@/components/CountryExplorer";
import { KNOWN_COUNTRY_NAMES } from "@/lib/countryCodes";
import { buildCountryRows, countryFromQuery, searchForSelection } from "@/lib/countryExplorer";
import { getShortlist, SHORTLIST_EVENT } from "@/lib/shortlist";
import type { Company, TrendingCompany } from "@/lib/types";

const AVATAR_GRADIENTS = [
  "from-sky to-purple",
  "from-brand to-brand-dark",
  "from-gold to-coral",
  "from-purple to-sky",
  "from-coral to-gold",
  "from-navy to-brand",
];

// A restrained pull from the Ndebele strip's palette, used as a rotating
// per-card left-edge accent so colour carries through the whole grid.
const CARD_ACCENTS = ["#e4322b", "#f5b301", "#2f9bf6", "#1a9e5f", "#ff7a1a"];

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i) | 0;
  return h;
}


function HospitalsDirectoryInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const loadedOnce = useRef(false);
  const pathname = usePathname();
  const [hospitals, setHospitals] = useState<Company[]>([]);
  const [trending, setTrending] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("South Africa");
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [shortlistIds, setShortlistIds] = useState<Set<string>>(new Set());
  const [previewCompany, setPreviewCompany] = useState<Company | null>(null);

  useEffect(() => {
    api.get<Company[]>("/companies?source_type=HOSPITAL&limit=5000&active=true")
      .then(setHospitals)
      .catch((e) => setErr(e.message));
    // Best-effort: a quiet directory with no watches yet just shows no badges.
    api.get<TrendingCompany[]>("/companies/trending?days=7&limit=200")
      .then((rows) => setTrending(new Set(rows.map((r) => r.company_id))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const sync = () => setShortlistIds(getShortlist());
    sync();
    window.addEventListener(SHORTLIST_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(SHORTLIST_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  // Deep link from a "Share" button elsewhere (?company=<id>), or from the
  // Coverage map (?country=<name>): jump straight to that view.
  useEffect(() => {
    const wanted = searchParams.get("company");
    const wantedCountry = searchParams.get("country");
    if (wanted && hospitals.length) {
      const found = hospitals.find((c) => c.id === wanted);
      if (found) {
        setCountry(found.country || "South Africa");
        setQ(found.company_name);
        return;
      }
    }
    if (wantedCountry) {
      // ?country= is a short code (ZA), "all" (every country) or, in older links, the full name.
      setCountry(countryFromQuery(wantedCountry, KNOWN_COUNTRY_NAMES) ?? wantedCountry);
      setShortlistOnly(false);
    } else if (loadedOnce.current) {
      // A bare URL after the page has opened (Back/Forward): the default view.
      setCountry("South Africa");
    }
    loadedOnce.current = true;
  }, [searchParams, hospitals]);

  const countryCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of hospitals) {
      const k = c.country || "";
      if (k) m[k] = (m[k] || 0) + 1;
    }
    return m;
  }, [hospitals]);

  const explorerRows = useMemo(() => {
    const withLinks: Record<string, number> = {};
    const counted: Record<string, number> = {};
    const openVacancies: Record<string, number> = {};
    for (const c of hospitals) {
      const k = c.country || "";
      if (!k) continue;
      if (c.careers_url) withLinks[k] = (withLinks[k] || 0) + 1;
      if (c.open_vacancies_known) counted[k] = (counted[k] || 0) + 1;
      openVacancies[k] = (openVacancies[k] || 0) + (c.open_vacancies || 0);
    }
    return buildCountryRows({ employers: countryCounts, withLinks, counted, openVacancies });
  }, [hospitals, countryCounts]);

  // Picking a country (list or map) updates the page and the address bar
  // (?country=ZA), so Back and a refresh land on the same country. "" is All countries.
  function chooseCountry(name: string) {
    setShortlistOnly(false);
    setCountry(name);
    router.push(`${pathname}${searchForSelection(window.location.search, name)}`, { scroll: false });
  }

  const shownHospitals = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = hospitals
      .filter((c) => shortlistOnly || !country || (c.country || "") === country)
      .filter((c) => !shortlistOnly || shortlistIds.has(c.id))
      .filter((c) => !needle || c.company_name.toLowerCase().includes(needle));
    return [...filtered].sort((a, b) => Number(!a.careers_url) - Number(!b.careers_url) || a.company_name.localeCompare(b.company_name));
  }, [hospitals, q, country, shortlistOnly, shortlistIds]);

  function surpriseMe() {
    if (!hospitals.length) return;
    const withLinks = hospitals.filter((c) => c.careers_url);
    const pool = withLinks.length ? withLinks : hospitals;
    const pick = pool[Math.floor(Math.random() * pool.length)];
    setShortlistOnly(false);
    setQ("");
    setCountry(pick.country || "South Africa");
    setPreviewCompany(pick);
  }

  const withLinks = hospitals.filter((c) => c.careers_url).length;
  const flag = COUNTRY_FLAGS[country] || "🌍";
  const countryTotal = country ? (countryCounts[country] ?? 0) : hospitals.length;
  const countryWithLinks = hospitals.filter((c) => (!country || (c.country || "") === country) && c.careers_url).length;

  const scoped = hospitals.filter((c) => !country || (c.country || "") === country);
  const explorerStats: ExplorerStats = {
    employers: scoped.length,
    withLinks: countryWithLinks,
    counted: scoped.filter((c) => c.open_vacancies_known).length,
    openVacancies: scoped.reduce((n, c) => n + (c.open_vacancies || 0), 0),
  };

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!hospitals.length) {
    return (
      <div className="mx-auto w-full max-w-xl space-y-4">
        <HowToUseCard steps={guideStepsFor(false)} loading loadingLabel="Loading hospitals…" />
        <FunSpinner label="Loading hospitals…" />
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Full-page decoration: the selected country's flag, watermarked across the page */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-0 overflow-hidden">
        <span className="absolute -right-16 top-16 select-none text-[18rem] leading-none opacity-[0.06]">{flag}</span>
        <span className="absolute -left-20 top-1/2 select-none text-[15rem] leading-none opacity-[0.05]">{flag}</span>
        <span className="absolute -right-10 bottom-8 select-none text-[13rem] leading-none opacity-[0.05]">{flag}</span>
      </div>

      <div className="relative z-10 space-y-6">
        {/* Desktop (lg+) drops this hero: the logo, notice, How to use card and Surprise me move into the explorer. */}
        <div className="overflow-hidden rounded-2xl shadow-sm lg:hidden">
          <Banner
            variant="companies"
            aside={<HowToUseCard steps={guideStepsFor(false)} />}
            eyebrow="Direct to employers"
            title="Hospital vacancies"
            subtitle={
              <>
                Browse hospital and healthcare-group openings and apply on each employer&apos;s own careers page.{" "}
                <strong className="text-ss-text"><AnimatedNumber value={hospitals.length} /></strong> hospitals ·{" "}
                <strong className="text-ss-text"><AnimatedNumber value={withLinks} /></strong> with direct careers links.
              </>
            }
          >
            <Button variant="secondary" onClick={surpriseMe}>🎲 Surprise me</Button>
          </Banner>
        </div>

        <CountryExplorer
          notice={<NotCountedNotice companies={shownHospitals} />}
          howTo={<HowToUseCard steps={guideStepsFor(false)} />}
          extraActions={<Button variant="secondary" onClick={surpriseMe}>🎲 Surprise me</Button>}
          rows={explorerRows}
          selected={shortlistOnly ? "" : country}
          onSelect={chooseCountry}
          stats={explorerStats}
          noun="hospitals"
          viewLabel="View all hospitals"
          onView={() => {
            setShortlistOnly(false);
            document.getElementById("explorer-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        />

        <Card>
          <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-ss-border pb-3">
            <p className="min-w-[12rem] flex-1 text-[11px] text-ss-muted">
              {country ? `Showing ${flag} ${country}.` : "All countries. Pick one in the list or on the map to narrow it."}
            </p>
              <button
                onClick={() => setShortlistOnly((v) => !v)}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                  shortlistOnly ? "bg-gold text-navy shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"
                }`}
              >
                ⭐ My shortlist
                <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${
                  shortlistOnly ? "bg-navy/15 text-navy" : "bg-ss-surface text-ss-muted"
                }`}>{shortlistIds.size}</span>
              </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-[14rem] flex-1">
              <Input
                placeholder="Search hospital…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
          </div>
        </Card>

        <p id="explorer-results" className="scroll-mt-24 text-sm text-ss-muted">
          Showing <strong className="text-ss-text">{shownHospitals.length}</strong> of{" "}
          {shortlistOnly ? shortlistIds.size : countryTotal} {shortlistOnly ? "shortlisted hospitals" : (country ? `hospitals in ${country}` : `hospitals in every country`)}.
        </p>

        <div className="empty:hidden lg:hidden"><NotCountedNotice companies={shownHospitals} /></div>

        <div className="grid gap-3 md:grid-cols-2">
          {shownHospitals.map((c) => {
            const accent = CARD_ACCENTS[Math.abs(hashCode(c.id)) % CARD_ACCENTS.length];
            return (
              <div
                key={c.id}
                onClick={() => setPreviewCompany(c)}
                style={{ borderLeftColor: accent }}
                className="relative cursor-pointer rounded-2xl border border-ss-border border-l-4 bg-ss-surface p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="absolute right-3 top-3" onClick={(e) => e.stopPropagation()}>
                  <ShortlistStar companyId={c.id} />
                </div>
                <div className="flex items-start justify-between gap-3 pr-6">
                  <div className="flex items-start gap-3">
                    <CompanyLogo
                      id={c.id}
                      hasIcon={!!c.has_icon}
                      name={c.company_name}
                      website={c.official_website}
                      careersUrl={c.careers_url}
                      country={c.country}
                      gradient={AVATAR_GRADIENTS[Math.abs(hashCode(c.id)) % AVATAR_GRADIENTS.length]}
                    />
                    <div>
                      <div className="font-semibold text-ss-text">{c.company_name}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className="rounded-full bg-coral/10 px-2 py-0.5 text-xs font-semibold text-coral">🏥 Hospital</span>
                        {isAtsPortal(c.careers_url) && (
                          <span className="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-semibold text-ss-text">Apply on their portal</span>
                        )}
                        {trending.has(c.id) && <TrendingBadge />}
                        {c.country && <span className="text-xs text-ss-muted">{c.country}</span>}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-ss-border pt-3 text-xs">
                  {c.careers_url && (
                    <>
                      <OpenVacancyCount company={c} />
                      <span className="text-ss-border">·</span>
                    </>
                  )}
                  <span className={c.careers_url ? "font-semibold text-brand-dark" : "text-ss-muted"}>
                    {c.careers_url ? "Direct careers link active ✓" : "No careers page yet"}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-stretch gap-3" onClick={(e) => e.stopPropagation()}>
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer" className="self-center">
                      <Button>View vacancies →</Button>
                    </a>
                  ) : (
                    <span className="whitespace-nowrap text-xs text-ss-muted">No careers page yet</span>
                  )}
                </div>

                <div onClick={(e) => e.stopPropagation()}>
                  <CompanyActionsRow company={c} shareBasePath="/hospitals" />
                </div>
              </div>
            );
          })}
          {shownHospitals.length === 0 && (
            <div className="md:col-span-2">
              <EmptyState
                icon={shortlistOnly ? "⭐" : "🔍"}
                title={shortlistOnly ? "Your shortlist is empty" : "No hospitals found"}
                message={shortlistOnly ? "Tap the ☆ on any card to add one." : "No hospitals match your search."}
              />
            </div>
          )}
        </div>

        <p className="text-center text-xs text-ss-muted">
          Wondering how complete this list really is?{" "}
          <Link href="/coverage" className="font-semibold text-brand-dark hover:underline">
            See the coverage map →
          </Link>
        </p>
      </div>

      {previewCompany && (
        <CompanyPreviewModal
          company={previewCompany}
          shareBasePath="/hospitals"
          onClose={() => setPreviewCompany(null)}
        />
      )}
    </div>
  );
}

export default function HospitalsDirectoryPage() {
  return (
    <Guard>
      <Suspense fallback={<Spinner label="Loading hospitals…" />}>
        <HospitalsDirectoryInner />
      </Suspense>
    </Guard>
  );
}
