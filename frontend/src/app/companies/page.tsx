"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Alert, Spinner, Select, EmptyState } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { NdebeleStrip } from "@/components/NdebeleStrip";
import { CircuitOverlay, GlowFrame } from "@/components/HighTech";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import { CompanyActionsRow, TrendingBadge, ShortlistStar } from "@/components/CompanyActions";
import { CompanyPreviewModal } from "@/components/CompanyPreviewModal";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { FunSpinner } from "@/components/FunSpinner";
import PendingSearchBanner from "@/components/PendingSearchBanner";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";

// South Africa's BRICS partners get their own dropdown beside the main country picker.
// Egypt and Ethiopia are African BRICS members, so they stay in the main list too.
const BRICS_PARTNERS = ["Brazil", "Russia", "India", "China", "Iran", "United Arab Emirates", "Indonesia", "Egypt", "Ethiopia"];
const BRICS_ONLY = new Set(BRICS_PARTNERS.slice(0, 7));
import { getShortlist, SHORTLIST_EVENT } from "@/lib/shortlist";
import type { Company, Vacancy, TrendingCompany } from "@/lib/types";

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
  DEPT: { label: "🏛️ Government department", cls: "bg-navy/10 text-navy" },
  PRIVATE: { label: "Private company", cls: "bg-gold/20 text-[#a9791a]" },
  NGO: { label: "🤝 NGO", cls: "bg-coral/10 text-coral" },
  UNI: { label: "🎓 University", cls: "bg-sky/10 text-sky" },
  COLLEGE: { label: "🏫 College", cls: "bg-teal/10 text-teal" },
  HOSPITAL: { label: "🏥 Hospital", cls: "bg-coral/10 text-coral" },
  SETA: { label: "🛠️ SETA", cls: "bg-[#1a9e5f]/10 text-[#137a48]" },
  SPORT: { label: "🏅 Sports association", cls: "bg-gold/20 text-[#a9791a]" },
  FED: { label: "🌐 Federation", cls: "bg-gold/20 text-[#a9791a]" },
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

type SortKey = "name" | "jobs" | "updated";

function CompaniesDirectoryInner() {
  const searchParams = useSearchParams();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [trending, setTrending] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<"all" | "listed" | "SOE" | "Municipality" | "Department" | "Private" | "NGO" | "University" | "College" | "Hospital" | "SETA" | "Sports" | "Federations">("all");
  const [country, setCountry] = useState("South Africa");
  const [sortBy, setSortBy] = useState<SortKey>("name");
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [shortlistIds, setShortlistIds] = useState<Set<string>>(new Set());
  const [previewCompany, setPreviewCompany] = useState<Company | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<Company[]>("/companies?limit=5000"),
      api.get<Vacancy[]>("/vacancies?is_open=true&limit=5000").catch(() => [] as Vacancy[]),
    ]).then(([cos, vacs]) => {
      setCompanies(cos);
      setVacancies(vacs);
    }).catch((e) => setErr(e.message));
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

  // Deep link from a "Share" button elsewhere (?company=<id>), the Coverage
  // map (?country=<name>), or the homepage's "SOE vacancies (SA)" shortcut
  // (?type=SOE&country=South%20Africa -- the same shortcut used to point at
  // the now-removed /jobs page).
  useEffect(() => {
    const wantedCompany = searchParams.get("company");
    const wantedCountry = searchParams.get("country");
    const wantedType = searchParams.get("type");
    if (wantedCompany && companies.length) {
      const found = companies.find((c) => c.id === wantedCompany);
      if (found) {
        setCountry(found.country || "South Africa");
        setQ(found.company_name);
        setFilter("all");
        return;
      }
    }
    if (wantedCountry) {
      setCountry(wantedCountry);
      setShortlistOnly(false);
    }
    if (wantedType && (FILTERS as readonly string[]).includes(wantedType)) {
      setFilter(wantedType as (typeof FILTERS)[number]);
    }
  }, [searchParams, companies]);

  // Real open-position counts per company, from the same vacancy data the
  // Find Jobs page uses -- never fabricated.
  const jobsByCompany = useMemo(() => {
    const m: Record<string, number> = {};
    for (const v of vacancies) m[v.company_id] = (m[v.company_id] || 0) + 1;
    return m;
  }, [vacancies]);

  const countries = useMemo(() => {
    const set = Array.from(new Set(companies.map((c) => c.country).filter(Boolean) as string[]));
    set.sort((a, b) => (a === "South Africa" ? -1 : b === "South Africa" ? 1 : a.localeCompare(b)));
    return set;
  }, [companies]);

  const countryCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of companies) {
      const k = c.country || "";
      if (k) m[k] = (m[k] || 0) + 1;
    }
    return m;
  }, [companies]);

  const shownCompanies = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = companies
      .filter((c) => shortlistOnly || filter === "Federations" || (c.country || "") === country)
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
        return st !== "SOE" && st !== "MUNI" && st !== "PRIVATE" && st !== "NGO" && st !== "UNI" && st !== "COLLEGE" && st !== "HOSPITAL" && st !== "SETA" && st !== "SPORT" && st !== "FED";
      })
      .filter((c) => !needle
        || c.company_name.toLowerCase().includes(needle)
        || (c.jse_code || "").toLowerCase().includes(needle));
    if (sortBy === "jobs") {
      return [...filtered].sort((a, b) => (jobsByCompany[b.id] || 0) - (jobsByCompany[a.id] || 0)
        || a.company_name.localeCompare(b.company_name));
    }
    if (sortBy === "updated") {
      return [...filtered].sort((a, b) => {
        const at = a.content_changed_at ? new Date(a.content_changed_at).getTime() : 0;
        const bt = b.content_changed_at ? new Date(b.content_changed_at).getTime() : 0;
        return bt - at || a.company_name.localeCompare(b.company_name);
      });
    }
    return [...filtered].sort((a, b) => a.company_name.localeCompare(b.company_name));
  }, [companies, q, filter, country, sortBy, jobsByCompany, shortlistOnly, shortlistIds]);

  function surpriseMe() {
    if (!companies.length) return;
    const withLinks = companies.filter((c) => c.careers_url);
    const pool = withLinks.length ? withLinks : companies;
    const pick = pool[Math.floor(Math.random() * pool.length)];
    setShortlistOnly(false);
    setFilter("all");
    setQ("");
    setCountry(pick.country || "South Africa");
    setPreviewCompany(pick);
  }

  const withLinks = companies.filter((c) => c.careers_url).length;
  const flag = COUNTRY_FLAGS[country] || "🌍";
  const fedTotal = companies.filter((c) => (c.source_type || "").toUpperCase() === "FED").length;
  const countryTotal = filter === "Federations" ? fedTotal : (countryCounts[country] ?? 0);
  const countryWithLinks = companies.filter((c) => (c.country || "") === country && c.careers_url).length;

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!companies.length) return <FunSpinner label="Loading the directory…" />;

  const FILTERS = ["all", "listed", "SOE", "Municipality", "Department", "Private", "NGO", "University", "College", "Hospital", "SETA", "Sports", "Federations"] as const;
  const filterLabel: Record<(typeof FILTERS)[number], string> = {
    all: "All", listed: "Listed", SOE: "State-owned", Municipality: "Municipalities",
    Department: "🏛️ Gov depts", Private: "Private", NGO: "🤝 NGOs", University: "🎓 Universities",
    College: "🏫 Colleges", Hospital: "🏥 Hospitals", SETA: "🛠️ SETAs", Sports: "🏅 Sports associations", Federations: "🌐 Continental & world federations",
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
          <NdebeleStrip id="companies-hero-top" palette="vivid" glow />
          <Banner
            variant="companies"
            eyebrow="Direct to employers"
            title="Companies & opportunities"
            subtitle={
              <>
                Browse the full directory and apply on each employer&apos;s official careers page.{" "}
                <strong className="text-white"><AnimatedNumber value={companies.length} /></strong> companies across Africa ·{" "}
                <strong className="text-white"><AnimatedNumber value={withLinks} /></strong> with direct careers links.
              </>
            }
          >
            <Button variant="secondary" glow onClick={surpriseMe}>🎲 Surprise me</Button>
          </Banner>
          <NdebeleStrip id="companies-hero-bottom" palette="vivid" flip glow />
        </div>

        <div className="ss-hud-card flex items-center gap-4 rounded-2xl border border-ss-border bg-ss-glass px-5 py-4 shadow-sm backdrop-blur-sm">
          <span aria-hidden className="ss-hud-scan !opacity-60 animate-scan-sweep" />
          <span className="text-5xl leading-none drop-shadow-sm">{flag}</span>
          <div>
            <div className="text-xl font-extrabold text-ss-text">{country}</div>
            <div className="ss-hud-tag text-xs text-ss-muted">
              <strong className="text-ss-text"><AnimatedNumber value={countryTotal} /></strong> employers mapped 📡 ·{" "}
              <strong className="text-ss-text"><AnimatedNumber value={countryWithLinks} /></strong> with a straight-to-jobs link 🚀
            </div>
          </div>
        </div>

        <GlowFrame ringClassName="rounded-2xl">
        <Card>
          {countries.length > 1 && (
            <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-ss-border pb-3">
              <div className="min-w-[12rem] flex-1 sm:max-w-xs">
                <Select
                  value={BRICS_ONLY.has(country) ? "" : country}
                  onChange={(e) => { if (e.target.value) { setShortlistOnly(false); setCountry(e.target.value); } }}
                  aria-label="Country"
                >
                  {BRICS_ONLY.has(country) && <option value="">Choose a country…</option>}
                  {countries.filter((cn) => !BRICS_ONLY.has(cn)).map((cn) => (
                    <option key={cn} value={cn}>
                      {COUNTRY_FLAGS[cn] || "🌍"} {cn} — {countryCounts[cn] ?? 0}
                    </option>
                  ))}
                </Select>
                <p className="ss-hud-tag mt-1 text-[10px] text-ss-muted">🌍 Pick a country to see its employers</p>
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

          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-[14rem] flex-1">
              <Input
                placeholder="Search company or JSE code…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
            <div className="min-w-[12rem] sm:max-w-xs">
              <Select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)} aria-label="Category">
                {FILTERS.map((f) => (
                  <option key={f} value={f}>{filterLabel[f]}</option>
                ))}
              </Select>
              <p className="ss-hud-tag mt-1 text-[10px] text-ss-muted">🗂️ Pick a category: state-owned, universities, hospitals and more</p>
            </div>
            <div className="w-full sm:ml-auto sm:w-auto">
            <label className="flex w-full items-center justify-between gap-2 text-xs text-ss-muted sm:w-auto sm:justify-start">
              Sort it by 🎛️
              <Select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortKey)}
                className="flex-1 sm:flex-none"
              >
                <option value="name">Name (A–Z)</option>
                <option value="jobs">Most jobs available</option>
                <option value="updated">Recently updated</option>
              </Select>
            </label>
            <p className="ss-hud-tag mt-1 text-[10px] text-ss-muted">🎛️ Choose how the cards are ordered</p>
            </div>
          </div>
        </Card>
        </GlowFrame>

        <p className="text-sm text-ss-muted">
          Showing <strong className="text-ss-text">{shownCompanies.length}</strong> of{" "}
          {shortlistOnly ? shortlistIds.size : countryTotal} {shortlistOnly ? "shortlisted companies" : filter === "Federations" ? "continental & world federations (all regions)" : `companies in ${country}`}. Pick a card, any card. 🃏
        </p>

        <div className="grid gap-3 md:grid-cols-2">
          {shownCompanies.map((c) => {
            const st = (c.source_type || "").toUpperCase();
            const isDept = st === "DEPT";
            const badge = typeBadge(c.source_type);
            const openJobs = jobsByCompany[c.id] || 0;
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
                          <span className="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-semibold text-navy">Apply on their portal</span>
                        )}
                        {trending.has(c.id) && <TrendingBadge />}
                        {c.country && <span className="text-xs text-ss-muted">{c.country}</span>}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-ss-border pt-3 text-xs">
                  {openJobs > 0 && (
                    <>
                      <span className="font-semibold text-brand-dark">
                        {`🔥 ${openJobs} open position${openJobs === 1 ? "" : "s"} right now`}
                      </span>
                      <span className="text-ss-border">·</span>
                    </>
                  )}
                  <span className={`ss-hud-tag ${c.careers_url ? "font-semibold text-brand-dark" : "text-ss-muted"}`}>
                    {c.careers_url ? <><span className="ss-hud-status mr-1.5 align-middle" />DIRECT LINK LIVE ⚡</> : "NO JOBS PAGE… YET 👀"}
                  </span>
                </div>

                <div className="mt-3" onClick={(e) => e.stopPropagation()}>
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer">
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
          {shownCompanies.length === 0 && (
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
          openJobs={jobsByCompany[previewCompany.id] || 0}
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
