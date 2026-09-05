"use client";

import { useEffect, useMemo, useState } from "react";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Alert, Spinner } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { NdebeleStrip } from "@/components/NdebeleStrip";
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

// Badge treatment per source_type -- bright, legible-on-white colours.
const TYPE_BADGE: Record<string, { label: string; cls: string }> = {
  SOE: { label: "State-owned", cls: "bg-purple/10 text-purple" },
  MUNI: { label: "Municipality", cls: "bg-teal/10 text-teal" },
  DEPT: { label: "🏛️ Government department", cls: "bg-navy/10 text-navy" },
  PRIVATE: { label: "Private company", cls: "bg-gold/20 text-[#a9791a]" },
  NGO: { label: "🤝 NGO", cls: "bg-coral/10 text-coral" },
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
  if (!companies.length) return <Spinner label="Loading the directory…" />;

  const FILTERS = ["all", "listed", "SOE", "Municipality", "Department", "Private", "NGO"] as const;
  const filterLabel: Record<(typeof FILTERS)[number], string> = {
    all: "All", listed: "Listed", SOE: "State-owned", Municipality: "Municipalities",
    Department: "🏛️ Gov depts", Private: "Private", NGO: "🤝 NGOs",
  };

  return (
    <div className="relative">
      {/* Full-page decoration: the selected country's flag, watermarked across the page */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-0 overflow-hidden">
        <span className="absolute -right-16 top-16 select-none text-[18rem] leading-none opacity-[0.06]">{flag}</span>
        <span className="absolute -left-20 top-1/2 select-none text-[15rem] leading-none opacity-[0.05]">{flag}</span>
        <span className="absolute -right-10 bottom-8 select-none text-[13rem] leading-none opacity-[0.05]">{flag}</span>
      </div>

      <div className="relative z-10 space-y-6">
        <div className="overflow-hidden rounded-2xl shadow-sm">
          <NdebeleStrip id="companies-hero-top" palette="vivid" />
          <Banner
            variant="companies"
            eyebrow="Direct to employers"
            title="Companies & opportunities"
            subtitle={
              <>
                Browse the full directory and apply on each employer&apos;s official careers page.{" "}
                <strong className="text-white">{companies.length}</strong> companies ·{" "}
                <strong className="text-white">{withLinks}</strong> with direct careers links.
              </>
            }
          />
          <NdebeleStrip id="companies-hero-bottom" palette="vivid" flip />
        </div>

        <div className="flex items-center gap-4 rounded-2xl border border-black/5 bg-white/70 px-5 py-4 shadow-sm backdrop-blur-sm">
          <span className="text-5xl leading-none drop-shadow-sm">{flag}</span>
          <div>
            <div className="text-xl font-extrabold text-navy">{country}</div>
            <div className="text-sm text-gray-500">
              <strong className="text-navy">{countryTotal}</strong> companies ·{" "}
              <strong className="text-navy">{countryWithLinks}</strong> with direct careers links
            </div>
          </div>
        </div>

        <Card>
          {countries.length > 1 && (
            <div className="mb-3 flex gap-1.5 overflow-x-auto border-b border-gray-100 pb-3 sm:flex-wrap sm:overflow-visible">
              {countries.map((cn) => {
                const active = country === cn;
                return (
                  <button
                    key={cn}
                    onClick={() => setCountry(cn)}
                    className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                      active ? "bg-navy text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    <span>{COUNTRY_FLAGS[cn] || "🌍"} {cn}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${
                      active ? "bg-white/20 text-white" : "bg-white text-gray-500"
                    }`}>{countryCounts[cn] ?? 0}</span>
                  </button>
                );
              })}
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
            <div className="flex flex-wrap gap-1">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition ${
                    filter === f ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {filterLabel[f]}
                </button>
              ))}
            </div>
            <label className="flex w-full items-center justify-between gap-2 text-xs text-gray-500 sm:ml-auto sm:w-auto sm:justify-start">
              Sort by
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortKey)}
                className="flex-1 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-700 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 sm:flex-none"
              >
                <option value="name">Name (A–Z)</option>
                <option value="jobs">Most jobs available</option>
              </select>
            </label>
          </div>
        </Card>

        <p className="text-sm text-gray-500">
          Showing <strong className="text-navy">{shownCompanies.length}</strong> of {countryTotal} companies in {country}.
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
                style={{ borderLeftColor: accent }}
                className="rounded-2xl border border-gray-200/80 border-l-4 bg-white p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <CompanyLogo
                      name={c.company_name}
                      website={c.official_website}
                      careersUrl={c.careers_url}
                      country={c.country}
                      gradient={AVATAR_GRADIENTS[Math.abs(hashCode(c.id)) % AVATAR_GRADIENTS.length]}
                      logoUrl={DEPARTMENT_LOGOS[c.company_name]}
                    />
                    <div>
                      <div className="font-semibold text-navy">{c.company_name}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.cls}`}>{badge.label}</span>
                        {c.jse_code && (
                          <span className="rounded-full bg-gold/20 px-2 py-0.5 text-xs font-semibold text-[#a9791a]">{c.jse_code}</span>
                        )}
                        {isAtsPortal(c.careers_url) && (
                          <span className="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-semibold text-navy">Apply on their portal</span>
                        )}
                        {c.country && <span className="text-xs text-gray-400">{c.country}</span>}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-gray-100 pt-3 text-xs">
                  <span className={openJobs > 0 ? "font-semibold text-brand-dark" : "text-gray-400"}>
                    {openJobs > 0 ? `${openJobs} open position${openJobs === 1 ? "" : "s"}` : "No open positions listed yet"}
                  </span>
                  <span className="text-gray-300">·</span>
                  <span className={c.careers_url ? "font-semibold text-brand-dark" : "text-gray-400"}>
                    {c.careers_url ? "Direct careers link active ✓" : "No careers page yet"}
                  </span>
                </div>

                <div className="mt-3">
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer">
                      <Button>{isDept ? "Visit department →" : "View jobs →"}</Button>
                    </a>
                  ) : (
                    <span className="whitespace-nowrap text-xs text-gray-400">No careers page yet</span>
                  )}
                </div>
              </div>
            );
          })}
          {shownCompanies.length === 0 && <p className="text-sm text-gray-400">No companies match your search.</p>}
        </div>
      </div>
    </div>
  );
}

export default function CompaniesDirectoryPage() {
  return (
    <Guard>
      <CompaniesDirectoryInner />
    </Guard>
  );
}
