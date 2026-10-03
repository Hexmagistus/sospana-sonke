"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Alert, Spinner, Select, EmptyState } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { CircuitOverlay, GlowFrame } from "@/components/HighTech";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import { CompanyActionsRow, OpenVacancyCount, TrendingBadge, ShortlistStar } from "@/components/CompanyActions";
import { CompanyPreviewModal } from "@/components/CompanyPreviewModal";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { FunSpinner } from "@/components/FunSpinner";
import PendingSearchBanner from "@/components/PendingSearchBanner";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";
import {
  DEFAULT_DIRECTORY_COUNTRY,
  DIRECTORY_COUNTRY_KEY,
  DIRECTORY_FILTERS,
  DIRECTORY_GUIDE_STEPS,
  FILTER_TO_TYPE,
  type DirectoryFilter,
  countryAfterFilterChange,
  countryFromDirectoryLink,
  readStoredCountry,
  directoryListPath,
  directorySliceKey,
  isDirectoryFilter,
  sortCountries,
} from "@/lib/directoryFilters";

// South Africa's BRICS partners get their own dropdown beside the main country picker.
// Egypt and Ethiopia are African BRICS members, so they stay in the main list too.
const BRICS_PARTNERS = ["Brazil", "Russia", "India", "China", "Iran", "United Arab Emirates", "Indonesia", "Egypt", "Ethiopia"];
const BRICS_ONLY = new Set(BRICS_PARTNERS.slice(0, 7));
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

// Verified logo images lifted directly from each department's own official
// website (not a favicon/Clearbit guess) -- keyed by exact company_name.
// Departments not listed here fall back to CompanyLogo's normal favicon
// lookup because no distinct logo image could be confirmed on their site
// (e.g. a legacy ASP.NET/SharePoint page with no separate crest asset) or
// the site could not be reached from here at all.
const DEPARTMENT_LOGOS: Record<string, string> = {
  "The Presidency": "https://www.thepresidency.gov.za/themes/gavias_edubiz/images/thepresidency.png",
  "Department of Cooperative Governance": "https://www.cogta.gov.za/cgta_2016/wp-content/uploads/2016/05/correctlogosmall-350x101.png",
  "Department of International Relations and Cooperation": "https://dirco.gov.za/wp-content/uploads/2020/04/DIRCO-website-header-1140x144.jpg",
  "South African Police Service": "https://www.saps.gov.za/_design/files/assets/images/top/saps_topBanner_sm_sm.jpg",
  "Department of Justice and Constitutional Development": "https://www.justice.gov.za/images/banner2020/home.gif",
  "Department of Correctional Services": "https://www.dcs.gov.za/wp-content/uploads/2017/01/cropped-newnew.png",
  "Department of Public Service and Administration": "https://www.dpsa.gov.za/site/templates/styles/images/header_small.png",
  "Department of Public Works and Infrastructure": "http://www.publicworks.gov.za/img/coatofarms.jpg",
  "Department of Communications and Digital Technologies": "https://www.dcdt.gov.za/images/dcdt/dcdt_banner.jpg",
  "Department of Water and Sanitation": "https://erecruitment.dws.gov.za/DWS-logo.png",
  "Department of Human Settlements": "https://www.dhs.gov.za/sites/default/files/images/logo.png",
  "Department of Transport": "https://www.transport.gov.za/wp-content/uploads/2023/02/newlogo.png",
  "Department of Electricity and Energy": "https://www.dee.gov.za/wp-content/uploads/2025/03/DDE-Logo1-scaled-e1773744806964.png",
  "Department of Trade Industry and Competition": "https://www.thedtic.gov.za/wp-content/uploads/cropped-The-dtic-logo-trade-industry-competition-Full-C-scaled-300x101.jpg",
  "Department of Small Business Development": "https://www.dsbd.gov.za/sites/default/files/2021-08/logo.png",
  "Department of Tourism": "https://www.tourism.gov.za/images/tourlogo.png",
  "Department of Forestry Fisheries and the Environment": "https://www.dffe.gov.za/sites/default/files/logo_0.png",
  "Department of Basic Education": "https://www.education.gov.za/Portals/0/dbeLogo2.png",
  "Department of Health": "https://a206977a.delivery.rocketcdn.me/wp-content/uploads/2024/03/Internet-header-Banner-768x67.png",
  "Department of Social Development": "https://www.dsd.gov.za/images/soc.png",
  "Department of Employment and Labour": "https://www.labour.gov.za/Style%20Library/_DOL/images/banner.jpg",
  "Department of Sport Arts and Culture": "https://www.dsac.gov.za/sites/default/files/logo_2.png",
  "Department of Women Youth and Persons with Disabilities": "https://dwypd.gov.za/wp-content/uploads/2020/07/logo-2.png",
};

// Badge treatment per source_type -- bright, legible-on-white colours.
const TYPE_BADGE: Record<string, { label: string; cls: string }> = {
  SOE: { label: "State-owned", cls: "bg-purple/10 text-purple" },
  MUNI: { label: "Municipality", cls: "bg-teal/10 text-teal" },
  DEPT: { label: "🏛️ Government department", cls: "bg-navy/10 text-ss-text" },
  PRIVATE: { label: "Private company", cls: "bg-gold/20 text-[#a9791a]" },
  NGO: { label: "🤝 NGO", cls: "bg-coral/10 text-coral" },
  UNI: { label: "🎓 University", cls: "bg-sky/10 text-sky" },
  COLLEGE: { label: "🏫 College", cls: "bg-teal/10 text-teal" },
  HOSPITAL: { label: "🏥 Hospital", cls: "bg-coral/10 text-coral" },
  SETA: { label: "🛠️ SETA", cls: "bg-[#1a9e5f]/10 text-[#137a48]" },
  SPORT: { label: "🏅 Sports association", cls: "bg-gold/20 text-[#a9791a]" },
  FED: { label: "🌐 Federation", cls: "bg-gold/20 text-[#a9791a]" },
  MUSIC: { label: "🎵 Music industry", cls: "bg-gold/20 text-[#a9791a]" },
};

function typeBadge(sourceType: string | null | undefined) {
  const st = (sourceType || "").toUpperCase();
  return TYPE_BADGE[st] || { label: sourceType ? `${st}-listed` : "Listed", cls: "bg-brand/10 text-brand-dark" };
}

// A restrained pull from the Ndebele strip's palette, used as a rotating
// per-card left-edge accent so colour carries through the whole grid.
const CARD_ACCENTS = ["#e4322b", "#f5b301", "#2f9bf6", "#1a9e5f", "#ff7a1a"];

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i) | 0;
  return h;
}


type Facets = {
  total: number;
  with_links: number;
  country_counts: Record<string, number>;
  country_with_links: Record<string, number>;
  type_counts: Record<string, number>;
};

function CompaniesDirectoryInner() {
  const searchParams = useSearchParams();
  // Only the slice on screen (one country, federations, or the shortlist) is
  // ever loaded -- the API no longer hands the whole directory to one request.
  const [companies, setCompanies] = useState<Company[]>([]);
  const [facets, setFacets] = useState<Facets | null>(null);
  const [sliceLoading, setSliceLoading] = useState(false);
  const sliceCache = useRef<Record<string, Company[]>>({});
  const [trending, setTrending] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<DirectoryFilter>("all");
  const [country, setCountry] = useState(DEFAULT_DIRECTORY_COUNTRY);
  const [guideOpen, setGuideOpen] = useState<boolean | null>(null);
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [shortlistIds, setShortlistIds] = useState<Set<string>>(new Set());
  const [previewCompany, setPreviewCompany] = useState<Company | null>(null);
  const storedCountryApplied = useRef(false);
  const countryRef = useRef(country);
  countryRef.current = country;

  useEffect(() => {
    api.get<Facets>("/companies/facets").then(setFacets).catch((e) => setErr(e.message));
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

  const globalType = FILTER_TO_TYPE[filter] ?? null;
  const sliceKey = directorySliceKey({
    shortlistKey: shortlistOnly ? Array.from(shortlistIds).sort().join(",") : null,
    sourceType: globalType,
    country,
  });

  useEffect(() => {
    if (!facets) return;
    const cached = sliceCache.current[sliceKey];
    if (cached) { setCompanies(cached); return; }
    let path: string;
    if (sliceKey.startsWith("ids:")) {
      const ids = sliceKey.slice(4);
      if (!ids) { setCompanies([]); return; }
      path = directoryListPath({ ids });
    } else {
      path = directoryListPath({ country, sourceType: globalType });
    }
    let cancelled = false;
    setSliceLoading(true);
    api.get<Company[]>(path)
      .then((rows) => {
        sliceCache.current[sliceKey] = rows;
        if (!cancelled) setCompanies(rows);
      })
      .catch((e) => { if (!cancelled) setErr(e.message); })
      .finally(() => { if (!cancelled) setSliceLoading(false); });
    return () => { cancelled = true; };
  }, [facets, sliceKey, country]);

  // Deep link from a "Share" button elsewhere (?company=<id>), the Coverage
  // map (?country=<name>), or a category shortcut such as /companies?type=SOE.
  // ?type= chooses the category only. It does not change the country.
  useEffect(() => {
    const wantedCompany = searchParams.get("company");
    const wantedCountry = searchParams.get("country");
    const wantedType = searchParams.get("type");
    if (wantedCompany) {
      api.get<Company[]>(`/companies?ids=${encodeURIComponent(wantedCompany)}`)
        .then(([found]) => {
          if (!found) return;
          setCountry(found.country || DEFAULT_DIRECTORY_COUNTRY);
          setQ(found.company_name);
          setFilter("all");
        })
        .catch(() => {});
      return;
    }
    if (!storedCountryApplied.current || wantedCountry) {
      const next = countryFromDirectoryLink({
        current: countryRef.current,
        urlCountry: wantedCountry,
        storedCountry: wantedCountry ? null : readStoredCountry(),
      });
      if (next !== countryRef.current) setCountry(next);
      if (wantedCountry) setShortlistOnly(false);
    }
    storedCountryApplied.current = true;
    if (isDirectoryFilter(wantedType)) {
      setFilter(wantedType);
      setShortlistOnly(false);
    }
  }, [searchParams]);

  useEffect(() => {
    try {
      setGuideOpen(localStorage.getItem("ss-directory-guide") !== "hidden");
    } catch {
      setGuideOpen(true);
    }
  }, []);

  useEffect(() => {
    const write = window.setTimeout(() => {
      try {
        localStorage.setItem(DIRECTORY_COUNTRY_KEY, country);
      } catch {
        /* private mode */
      }
    }, 0);
    return () => window.clearTimeout(write);
  }, [country]);

  const countryCounts: Record<string, number> = facets?.country_counts ?? {};
  const countries = useMemo(
    () => sortCountries(Object.keys(facets?.country_counts ?? {})),
    [facets],
  );

  const shownCompanies = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = companies
      // A category and a country are fetched together. An empty country is
      // "All countries", and only the country control sets that.
      .filter((c) => shortlistOnly || !country || (c.country || "") === country)
      .filter((c) => !shortlistOnly || shortlistIds.has(c.id))
      .filter((c) => {
        if (filter === "all") return true;
        const st = (c.source_type || "").toUpperCase();
        if (filter === "SOE") return st === "SOE";
        if (filter === "Municipality") return st === "MUNI";
        if (filter === "Department") return st === "DEPT";
        if (filter === "Private") return st === "PRIVATE";
        if (filter === "NGO") return st === "NGO";
        if (filter === "University") return st === "UNI";
        if (filter === "College") return st === "COLLEGE";
        if (filter === "Hospital") return st === "HOSPITAL";
        if (filter === "SETA") return st === "SETA";
        if (filter === "Sports") return st === "SPORT";
        if (filter === "Federations") return st === "FED";
        if (filter === "Music") return st === "MUSIC";
        return st !== "SOE" && st !== "MUNI" && st !== "PRIVATE" && st !== "NGO" && st !== "UNI" && st !== "COLLEGE" && st !== "HOSPITAL" && st !== "SETA" && st !== "SPORT" && st !== "FED" && st !== "MUSIC";
      })
      .filter((c) => !needle
        || c.company_name.toLowerCase().includes(needle)
        || (c.jse_code || "").toLowerCase().includes(needle));
    return [...filtered].sort((a, b) => Number(!a.careers_url) - Number(!b.careers_url) || a.company_name.localeCompare(b.company_name));
  }, [companies, q, filter, country, globalType, shortlistOnly, shortlistIds]);

  function surpriseMe() {
    api.get<Company>("/companies/surprise").then((pick) => {
      setShortlistOnly(false);
      setFilter("all");
      setQ("");
      setCountry(pick.country || "South Africa");
      setPreviewCompany(pick);
    }).catch(() => {});
  }

  // A category click never changes the country. All and Listed still need
  // one, so a blank "every country" choice becomes South Africa again.
  function selectFilter(f: DirectoryFilter) {
    setFilter(f);
    setCountry((current) => countryAfterFilterChange(current, f));
  }

  const withLinks = facets?.with_links ?? 0;
  const flag = COUNTRY_FLAGS[country] || "🌍";
  // Category totals come from the loaded slice (country and category together).
  // The dropdown counts stay the full per-country facet numbers.
  const inCategoryScope = globalType ? companies.filter((c) => !country || (c.country || "") === country) : companies;
  const countryTotal = globalType ? inCategoryScope.length : (countryCounts[country] ?? 0);
  const countryWithLinks = globalType
    ? inCategoryScope.filter((c) => c.careers_url).length
    : (facets?.country_with_links?.[country] ?? 0);

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!facets) return <FunSpinner label="Loading the directory…" />;

  const filterLabel: Record<DirectoryFilter, string> = {
    all: "All", listed: "Listed", SOE: "State-owned", Municipality: "Municipalities",
    Department: "🏛️ Gov depts", Private: "Private", NGO: "🤝 NGOs", University: "🎓 Universities",
    College: "🏫 Colleges", Hospital: "🏥 Hospitals", SETA: "🛠️ SETAs", Sports: "🏅 Sports associations", Federations: "🌐 Federations", Music: "🎵 Music industry",
  };

  return (
    <div className="relative">
      <CircuitOverlay className="-z-10 opacity-70" opacity={0.07} stroke="#0b1f3a" dotColor="#f5b301" />
      {/* Full-page decoration: the selected country's flag, watermarked across the page */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-0 overflow-hidden">
        <span className="absolute -right-16 top-16 select-none text-[18rem] leading-none opacity-[0.06]">{flag}</span>
        <span className="absolute -left-20 top-1/2 select-none text-[15rem] leading-none opacity-[0.05]">{flag}</span>
        <span className="absolute -right-10 bottom-8 select-none text-[13rem] leading-none opacity-[0.05]">{flag}</span>
      </div>

      <div className="relative z-10 space-y-6">
        <PendingSearchBanner />
        <div className="overflow-hidden rounded-2xl shadow-sm">
          <Banner
            variant="companies"
            eyebrow="Direct to employers"
            title="Companies & opportunities"
            subtitle={
              <>
                Browse the full directory and apply on each employer&apos;s official careers page.{" "}
                <strong className="text-white"><AnimatedNumber value={facets.total} /></strong> companies in the directory ·{" "}
                <strong className="text-white"><AnimatedNumber value={withLinks} /></strong> with direct careers links.
              </>
            }
          >
            <Button variant="secondary" glow onClick={surpriseMe}>🎲 Surprise me</Button>
          </Banner>
        </div>

        <div className="ss-hud-card flex items-center gap-4 rounded-2xl border border-ss-border bg-ss-glass px-5 py-4 shadow-sm backdrop-blur-sm">
          <span aria-hidden className="ss-hud-scan !opacity-60 animate-scan-sweep" />
          <span className="text-5xl leading-none drop-shadow-sm">{flag}</span>
          <div>
            <div className="text-xl font-extrabold text-ss-text">
              {globalType ? (country ? `${filterLabel[filter]} · ${country}` : `${filterLabel[filter]} — every country`) : country}
            </div>
            <div className="ss-hud-tag text-xs text-ss-muted">
              <strong className="text-ss-text"><AnimatedNumber value={countryTotal} /></strong> employers mapped 📡 ·{" "}
              <strong className="text-ss-text"><AnimatedNumber value={countryWithLinks} /></strong> with a straight-to-jobs link 🚀
            </div>
          </div>
        </div>

        <GlowFrame ringClassName="rounded-2xl">
        <Card>
          {guideOpen === null ? null : guideOpen ? (
            <section aria-label="How to use" className="mb-4 rounded-xl border border-gold/50 bg-gold/10 p-3 dark:bg-navy/50 sm:p-4">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h2 className="text-sm font-extrabold text-navy dark:text-gold">How to use</h2>
                <button
                  type="button"
                  className="shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold text-navy hover:bg-gold/20 dark:text-gold"
                  onClick={() => {
                    setGuideOpen(false);
                    try { localStorage.setItem("ss-directory-guide", "hidden"); } catch { /* private mode */ }
                  }}
                >
                  Hide
                </button>
              </div>
              <ol className="grid gap-2 sm:grid-cols-2">
                {DIRECTORY_GUIDE_STEPS.map((step, i) => (
                  <li key={step} className="flex min-w-0 items-start gap-2 text-sm leading-snug text-ss-text">
                    <span aria-hidden className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold text-[11px] font-extrabold text-navy">
                      {i + 1}
                    </span>
                    <span className="min-w-0">{step}</span>
                  </li>
                ))}
              </ol>
            </section>
          ) : (
            <button
              type="button"
              className="mb-3 rounded-full border border-gold/50 bg-gold/10 px-3 py-1 text-xs font-semibold text-navy hover:bg-gold/20 dark:text-gold"
              onClick={() => {
                setGuideOpen(true);
                try { localStorage.removeItem("ss-directory-guide"); } catch { /* private mode */ }
              }}
            >
              How to use
            </button>
          )}
          {countries.length > 1 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-ss-border pb-3">
              <div className="min-w-[12rem] flex-1 sm:max-w-xs">
                <Select
                  value={BRICS_ONLY.has(country) ? "" : country}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (!v && !globalType) return; // inert placeholder outside category mode
                    setShortlistOnly(false);
                    setCountry(v);
                  }}
                  aria-label="Country"
                >
                  {globalType
                    ? <option value="">🌍 All countries</option>
                    : (BRICS_ONLY.has(country) && <option value="">Choose a country…</option>)}
                  {countries.filter((cn) => !BRICS_ONLY.has(cn)).map((cn) => (
                    <option key={cn} value={cn}>
                      {COUNTRY_FLAGS[cn] || "🌍"} {cn} — {countryCounts[cn] ?? 0}
                    </option>
                  ))}
                </Select>
                <p className="ss-hud-tag mt-1 text-[10px] text-ss-muted">
                  {country
                    ? "Your country stays when you pick a category."
                    : "All countries. Pick one whenever you want to narrow the list."}
                </p>
              </div>
              {BRICS_PARTNERS.some((cn) => (countryCounts[cn] ?? 0) > 0) && (
                <div className="min-w-[12rem] flex-1 sm:max-w-xs">
                  <Select
                    value={BRICS_PARTNERS.includes(country) ? country : ""}
                    onChange={(e) => { if (e.target.value) { setShortlistOnly(false); setCountry(e.target.value); } }}
                    aria-label="BRICS partners"
                  >
                    <option value="">🌐 BRICS partners…</option>
                    {BRICS_PARTNERS.filter((cn) => (countryCounts[cn] ?? 0) > 0).map((cn) => (
                      <option key={cn} value={cn}>
                        {COUNTRY_FLAGS[cn] || "🌍"} {cn} — {countryCounts[cn] ?? 0}
                      </option>
                    ))}
                  </Select>
                  <p className="ss-hud-tag mt-1 text-[10px] text-ss-muted">🌐 Pick a BRICS partner country to browse its employers</p>
                </div>
              )}
              <button
                onClick={() => setShortlistOnly((v) => !v)}
                className={`flex shrink-0 flex-col items-center rounded-xl px-3.5 py-1.5 leading-tight transition ${
                  shortlistOnly ? "bg-gold text-white shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"
                }`}
              >
                <span className="text-sm font-semibold">⭐ My shortlist</span>
                <span className={`text-[11px] font-bold tabular-nums ${shortlistOnly ? "text-white/85" : "text-ss-muted"}`}>
                  {shortlistIds.size} saved
                </span>
              </button>
            </div>
          )}

          <div className="min-w-[14rem]">
            <Input
              placeholder="Search company or JSE code…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {DIRECTORY_FILTERS.map((f) => {
              const active = filter === f;
              const st = FILTER_TO_TYPE[f];
              const count = st ? (facets.type_counts?.[st] ?? 0) : null;
              return (
                <button
                  key={f}
                  onClick={() => selectFilter(f)}
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                    active ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"
                  }`}
                >
                  <span>{filterLabel[f]}</span>
                  {count !== null && (
                    <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${active ? "bg-white/20 text-white" : "bg-ss-surface text-ss-muted"}`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <p className="ss-hud-tag mt-1.5 text-[10px] text-ss-muted">
            {globalType && country
              ? `Showing ${filterLabel[filter]} in ${country}.`
              : globalType
                ? "Showing this category in every country. Pick a country above to narrow it."
                : "Pick a category. The country you chose stays selected."}
          </p>
        </Card>
        </GlowFrame>

        <div className="ss-hud-card flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-ss-border bg-ss-glass px-4 py-3 backdrop-blur-sm">
          <span aria-hidden className="ss-hud-scan !opacity-40 animate-scan-sweep" />
          <span className="ss-hud-tag flex items-center gap-2 text-[11px] font-bold text-brand-dark">
            <span className="ss-hud-status" /> Live scan
          </span>
          <span className="flex items-baseline gap-1.5">
            <span className="bg-gradient-to-r from-brand to-gold bg-clip-text text-3xl font-black tabular-nums leading-none text-transparent">
              <AnimatedNumber value={shownCompanies.length} />
            </span>
            <span className="ss-hud-tag text-xs text-ss-muted">
              / {shortlistOnly ? shortlistIds.size : countryTotal} {shortlistOnly ? "shortlisted" : "in range"}
            </span>
          </span>
          <span className="ss-hud-tag rounded-md border border-ss-border bg-ss-surface px-2 py-1 text-[11px] font-semibold text-ss-text">
            Category · {filterLabel[filter]}
          </span>
          <span className="ss-hud-tag rounded-md border border-ss-border bg-ss-surface px-2 py-1 text-[11px] font-semibold text-ss-text">
            Zone · {globalType ? (country ? `${flag} ${country}` : "🌍 All countries") : shortlistOnly ? "⭐ My shortlist" : `${flag} ${country}`}
          </span>
          <span className="ss-hud-tag text-[11px] text-ss-muted sm:ml-auto">Pick a card, any card 🃏</span>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {shownCompanies.map((c) => {
            const st = (c.source_type || "").toUpperCase();
            const isDept = st === "DEPT";
            const badge = typeBadge(c.source_type);
            const accent = CARD_ACCENTS[Math.abs(hashCode(c.id)) % CARD_ACCENTS.length];
            return (
              <div
                key={c.id}
                onClick={() => setPreviewCompany(c)}
                style={{ borderLeftColor: accent }}
                className="ss-hud-card cursor-pointer rounded-2xl border border-ss-border border-l-4 bg-ss-surface p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] hover:-translate-y-0.5"
              >
                <span aria-hidden className="ss-hud-scan" />
                <div className="absolute right-3 top-3" onClick={(e) => e.stopPropagation()}>
                  <ShortlistStar companyId={c.id} />
                </div>
                <div className="flex items-start justify-between gap-3 pr-6">
                  <div className="flex items-start gap-3">
                    <CompanyLogo
                      id={c.id}
                      name={c.company_name}
                      website={c.official_website}
                      careersUrl={c.careers_url}
                      country={c.country}
                      gradient={AVATAR_GRADIENTS[Math.abs(hashCode(c.id)) % AVATAR_GRADIENTS.length]}
                      logoUrl={DEPARTMENT_LOGOS[c.company_name]}
                    />
                    <div>
                      <div className="font-semibold text-ss-text">{c.company_name}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.cls}`}>{badge.label}</span>
                        {c.jse_code && (
                          <span className="rounded-full bg-gold/20 px-2 py-0.5 text-xs font-semibold text-[#a9791a]">{c.jse_code}</span>
                        )}
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
                  <span className={`ss-hud-tag ${c.careers_url ? "font-semibold text-brand-dark" : "text-ss-muted"}`}>
                    {c.careers_url ? <><span className="ss-hud-status mr-1.5 align-middle" />DIRECT LINK LIVE ⚡</> : "NO JOBS PAGE… YET 👀"}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-stretch gap-3" onClick={(e) => e.stopPropagation()}>
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer" className="self-center">
                      <Button>{isDept ? "Visit department →" : "View jobs →"}</Button>
                    </a>
                  ) : (
                    <span className="whitespace-nowrap text-xs text-ss-muted">Still hunting for their careers page 🕵️</span>
                  )}
                </div>

                <div onClick={(e) => e.stopPropagation()}>
                  <CompanyActionsRow company={c} shareBasePath="/companies" />
                </div>
              </div>
            );
          })}
          {sliceLoading && shownCompanies.length === 0 && (
            <div className="md:col-span-2">
              <FunSpinner label={`Rounding up employers in ${country}…`} />
            </div>
          )}
          {!sliceLoading && shownCompanies.length === 0 && (
            <div className="md:col-span-2">
              <EmptyState
                icon={shortlistOnly ? "⭐" : "🔍"}
                title={shortlistOnly ? "Nothing starred yet ✨" : "Hmm, the radar found nothing 🛰️"}
                message={shortlistOnly ? "Tap the ☆ on any card and it lands here, ready when you are." : "Try a different spelling, or clear a filter and go again."}
              />
            </div>
          )}
        </div>

        <p className="text-center text-xs text-ss-muted">
          Curious how much of the map we've covered? 🗺️{" "}
          <Link href="/coverage" className="font-semibold text-brand-dark hover:underline">
            Explore the coverage map →
          </Link>
        </p>
      </div>

      {previewCompany && (
        <CompanyPreviewModal
          company={previewCompany}
          shareBasePath="/companies"
          onClose={() => setPreviewCompany(null)}
        />
      )}
    </div>
  );
}

export default function CompaniesDirectoryPage() {
  return (
    <Guard>
      <Suspense fallback={<Spinner label="Loading the directory…" />}>
        <CompaniesDirectoryInner />
      </Suspense>
    </Guard>
  );
}
