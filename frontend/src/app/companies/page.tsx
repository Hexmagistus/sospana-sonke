"use client";

import { useEffect, useMemo, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Alert, Spinner } from "@/components/ui";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import type { Company, Vacancy } from "@/lib/types";

const AVATAR_GRADIENTS = [
  "from-sky to-purple",
  "from-brand to-brand-dark",
  "from-gold to-coral",
  "from-purple to-sky",
  "from-coral to-gold",
  "from-navy to-brand",
];

const COUNTRY_FLAGS: Record<string, string> = {
  "South Africa": "🇿🇦", "Lesotho": "🇱🇸", "Botswana": "🇧🇼", "Namibia": "🇳🇦",
  "Eswatini": "🇸🇿", "Zimbabwe": "🇿🇼", "Mozambique": "🇲🇿",
  "Malawi": "🇲🇼", "Mauritius": "🇲🇺", "Zambia": "🇿🇲",
  "Tanzania": "🇹🇿", "Angola": "🇦🇴",
  "Madagascar": "🇲🇬", "DR Congo": "🇨🇩", "Seychelles": "🇸🇨", "Comoros": "🇰🇲",
};

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

// Badge treatment per source_type, kept to the palette above (navy / teal /
// emerald / gold / muted) rather than introducing new colours.
const TYPE_BADGE: Record<string, { label: string; cls: string }> = {
  SOE: { label: "State-owned", cls: "bg-[#087F73]/20 text-[#5EEAD4] ring-1 ring-[#087F73]/40" },
  MUNI: { label: "Municipality", cls: "bg-[#0A3150] text-[#A8B5C5] ring-1 ring-white/10" },
  DEPT: { label: "🏛️ Government department", cls: "bg-[#0A3150] text-[#A8B5C5] ring-1 ring-white/10" },
  PRIVATE: { label: "Private company", cls: "bg-white/10 text-[#F8FAFC] ring-1 ring-white/15" },
  NGO: { label: "🤝 NGO", cls: "bg-[#20B26B]/15 text-[#6EE7B7] ring-1 ring-[#20B26B]/40" },
};

function typeBadge(sourceType: string | null | undefined) {
  const st = (sourceType || "").toUpperCase();
  return TYPE_BADGE[st] || { label: sourceType ? `${st}-listed` : "Listed", cls: "bg-[#F5B900]/15 text-[#F5B900] ring-1 ring-[#F5B900]/30" };
}

type SortKey = "name" | "jobs";

function CompaniesDirectoryInner() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<"all" | "listed" | "SOE" | "Municipality" | "Department" | "Private" | "NGO">("all");
  const [country, setCountry] = useState("South Africa");
  const [sortBy, setSortBy] = useState<SortKey>("name");

  useEffect(() => {
    Promise.all([
      api.get<Company[]>("/companies?limit=5000"),
      api.get<Vacancy[]>("/vacancies?is_open=true&limit=5000").catch(() => [] as Vacancy[]),
    ]).then(([cos, vacs]) => {
      setCompanies(cos);
      setVacancies(vacs);
    }).catch((e) => setErr(e.message));
  }, []);

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
      .filter((c) => (c.country || "") === country)
      .filter((c) => {
        if (filter === "all") return true;
        const st = (c.source_type || "").toUpperCase();
        if (filter === "SOE") return st === "SOE";
        if (filter === "Municipality") return st === "MUNI";
        if (filter === "Department") return st === "DEPT";
        if (filter === "Private") return st === "PRIVATE";
        if (filter === "NGO") return st === "NGO";
        return st !== "SOE" && st !== "MUNI" && st !== "PRIVATE" && st !== "NGO";
      })
      .filter((c) => !needle
        || c.company_name.toLowerCase().includes(needle)
        || (c.jse_code || "").toLowerCase().includes(needle));
    if (sortBy === "jobs") {
      return [...filtered].sort((a, b) => (jobsByCompany[b.id] || 0) - (jobsByCompany[a.id] || 0)
        || a.company_name.localeCompare(b.company_name));
    }
    return [...filtered].sort((a, b) => a.company_name.localeCompare(b.company_name));
  }, [companies, q, filter, country, sortBy, jobsByCompany]);

  const withLinks = companies.filter((c) => c.careers_url).length;
  const flag = COUNTRY_FLAGS[country] || "🌍";
  const countryTotal = countryCounts[country] ?? 0;
  const countryWithLinks = companies.filter((c) => (c.country || "") === country && c.careers_url).length;

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!companies.length) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading the directory…" />
      </div>
    );
  }

  const FILTERS = ["all", "listed", "SOE", "Municipality", "Department", "Private", "NGO"] as const;
  const filterLabel: Record<(typeof FILTERS)[number], string> = {
    all: "All", listed: "Listed", SOE: "State-owned", Municipality: "Municipalities",
    Department: "🏛️ Gov depts", Private: "Private", NGO: "🤝 NGOs",
  };

  return (
    <div className="-mx-4 min-h-[calc(100vh-4rem)] bg-[#031525] px-4 pb-12 pt-6 sm:px-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* ---------------- Hero ---------------- */}
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-[#08233D] via-[#0A3150] to-[#031525] p-6 shadow-[0_0_60px_-20px_rgba(8,127,115,0.35)] sm:p-8">
          {/* subtle premium-tech texture: dot grid + glows, no literal imagery */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.35]"
            style={{
              backgroundImage: "radial-gradient(rgba(255,255,255,0.14) 1px, transparent 1px)",
              backgroundSize: "22px 22px",
              maskImage: "radial-gradient(ellipse at top right, black, transparent 70%)",
            }}
          />
          <div aria-hidden className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full bg-[#087F73]/25 blur-3xl" />
          <div aria-hidden className="pointer-events-none absolute -bottom-24 left-10 h-56 w-56 rounded-full bg-[#F5B900]/10 blur-3xl" />

          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-xl">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#F5B900]">Direct to employers</p>
              <h1 className="text-3xl font-extrabold text-[#F8FAFC] sm:text-4xl">Companies &amp; opportunities</h1>
              <p className="mt-2 text-sm text-[#A8B5C5] sm:text-base">
                Browse the full directory and apply on each employer&apos;s official careers page.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#087F73]/20 text-lg">🏢</span>
                  <div>
                    <div className="text-lg font-extrabold leading-none text-[#F8FAFC]">{companies.length.toLocaleString()}</div>
                    <div className="text-xs text-[#A8B5C5]">Companies</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#20B26B]/20 text-lg">🔗</span>
                  <div>
                    <div className="text-lg font-extrabold leading-none text-[#F8FAFC]">{withLinks.toLocaleString()}</div>
                    <div className="text-xs text-[#A8B5C5]">Direct careers links</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ---------------- Country summary + pills ---------------- */}
        <div className="rounded-2xl border border-white/10 bg-[#08233D] p-5">
          <div className="flex items-center gap-4 border-b border-white/10 pb-4">
            <span className="text-4xl leading-none">{flag}</span>
            <div>
              <div className="text-lg font-extrabold text-[#F8FAFC]">{country}</div>
              <div className="text-sm text-[#A8B5C5]">
                <strong className="text-[#F8FAFC]">{countryTotal}</strong> companies ·{" "}
                <strong className="text-[#F8FAFC]">{countryWithLinks}</strong> with direct careers links
              </div>
            </div>
          </div>

          {countries.length > 1 && (
            <div className="flex flex-wrap gap-1.5 overflow-x-auto pt-4">
              {countries.map((cn) => {
                const active = country === cn;
                return (
                  <button
                    key={cn}
                    onClick={() => setCountry(cn)}
                    className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                      active
                        ? "bg-[#20B26B]/15 text-[#F8FAFC] shadow-[0_0_0_1px_rgba(32,178,107,0.6),0_0_16px_-2px_rgba(32,178,107,0.5)]"
                        : "bg-white/5 text-[#A8B5C5] hover:bg-white/10 hover:text-[#F8FAFC]"
                    }`}
                  >
                    <span>{COUNTRY_FLAGS[cn] || "🌍"} {cn}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${
                      active ? "bg-[#20B26B]/25 text-[#6EE7B7]" : "bg-white/10 text-[#A8B5C5]"
                    }`}>{countryCounts[cn] ?? 0}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* ---------------- Search + filters ---------------- */}
        <div className="rounded-2xl border border-white/10 bg-[#08233D] p-5">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[14rem] flex-1">
              <svg viewBox="0 0 20 20" fill="none" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#A8B5C5]">
                <circle cx="9" cy="9" r="6.5" stroke="currentColor" strokeWidth="1.6" />
                <path d="M18 18l-4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              <input
                placeholder="Search company or JSE code…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="w-full rounded-lg border border-white/15 bg-white/5 py-2.5 pl-9 pr-3.5 text-sm text-[#F8FAFC] placeholder:text-[#6E7F94] transition focus:border-[#087F73] focus:outline-none focus:ring-2 focus:ring-[#087F73]/30"
              />
            </div>
            <div className="flex flex-wrap gap-1">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap transition ${
                    filter === f
                      ? "bg-[#F5B900] text-[#031525] shadow-sm"
                      : "bg-white/5 text-[#A8B5C5] hover:bg-white/10 hover:text-[#F8FAFC]"
                  }`}
                >
                  {filterLabel[f]}
                </button>
              ))}
            </div>
            <label className="ml-auto flex items-center gap-2 text-xs text-[#A8B5C5]">
              Sort by
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortKey)}
                className="rounded-md border border-white/15 bg-white/5 px-2.5 py-1.5 text-sm text-[#F8FAFC] focus:border-[#087F73] focus:outline-none focus:ring-2 focus:ring-[#087F73]/30"
              >
                <option className="bg-[#08233D]" value="name">Name (A–Z)</option>
                <option className="bg-[#08233D]" value="jobs">Most jobs available</option>
              </select>
            </label>
          </div>
        </div>

        {/* ---------------- Results ---------------- */}
        <p className="text-sm text-[#A8B5C5]">
          Showing <strong className="text-[#F8FAFC]">{shownCompanies.length}</strong> of {countryTotal} companies in {country}.
        </p>

        <div className="grid gap-3 md:grid-cols-2">
          {shownCompanies.map((c) => {
            const st = (c.source_type || "").toUpperCase();
            const isDept = st === "DEPT";
            const badge = typeBadge(c.source_type);
            const openJobs = jobsByCompany[c.id] || 0;
            return (
              <div
                key={c.id}
                className="group rounded-2xl border border-white/10 bg-[#08233D] p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-[#087F73]/50 hover:shadow-[0_8px_30px_-12px_rgba(8,127,115,0.5)]"
              >
                <div className="flex items-start gap-3">
                  <CompanyLogo
                    name={c.company_name}
                    website={c.official_website}
                    careersUrl={c.careers_url}
                    country={c.country}
                    gradient={AVATAR_GRADIENTS[Math.abs(hashCode(c.id)) % AVATAR_GRADIENTS.length]}
                    logoUrl={DEPARTMENT_LOGOS[c.company_name]}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold text-[#F8FAFC]">{c.company_name}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.cls}`}>{badge.label}</span>
                      {c.jse_code && (
                        <span className="rounded-full bg-[#F5B900]/15 px-2 py-0.5 text-xs font-semibold text-[#F5B900] ring-1 ring-[#F5B900]/30">{c.jse_code}</span>
                      )}
                      {isAtsPortal(c.careers_url) && (
                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-medium text-[#A8B5C5]">Apply on their portal</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-white/10 pt-4 text-sm">
                  <div>
                    <div className="text-xs text-[#6E7F94]">Location</div>
                    <div className="font-medium text-[#F8FAFC]">{c.country}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#6E7F94]">Jobs available</div>
                    <div className={`font-medium ${openJobs > 0 ? "text-[#6EE7B7]" : "text-[#6E7F94]"}`}>
                      {openJobs > 0 ? `${openJobs} open position${openJobs === 1 ? "" : "s"}` : "None listed yet"}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs text-[#6E7F94]">Direct careers link</div>
                    <div className={`font-medium ${c.careers_url ? "text-[#6EE7B7]" : "text-[#6E7F94]"}`}>
                      {c.careers_url ? "Active ✓" : "Not available yet"}
                    </div>
                  </div>
                </div>

                <div className="mt-4">
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer">
                      <span className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#F5B900] px-4 py-2 text-sm font-semibold text-[#031525] shadow-sm transition hover:brightness-110 active:scale-[0.98]">
                        {isDept ? "Visit department" : "View jobs"}
                        <svg viewBox="0 0 20 20" fill="none" className="h-3.5 w-3.5"><path d="M7 13l6-6M13 7H8m5 0v5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                      </span>
                    </a>
                  ) : (
                    <span className="block rounded-lg border border-white/10 px-4 py-2 text-center text-xs text-[#6E7F94]">No careers page yet</span>
                  )}
                </div>
              </div>
            );
          })}
          {shownCompanies.length === 0 && (
            <p className="col-span-2 rounded-2xl border border-white/10 bg-[#08233D] p-6 text-center text-sm text-[#A8B5C5]">
              No companies match your search.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// Cheap deterministic hash so each company gets a stable (not literally
// random) avatar gradient without depending on list position/index.
function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i) | 0;
  return h;
}

export default function CompaniesDirectoryPage() {
  return (
    <Guard>
      <CompaniesDirectoryInner />
    </Guard>
  );
}
