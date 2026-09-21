"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Alert, Spinner, Select, EmptyState } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { NdebeleStrip } from "@/components/NdebeleStrip";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import { CompanyActionsRow, TrendingBadge, ShortlistStar } from "@/components/CompanyActions";
import { CompanyPreviewModal } from "@/components/CompanyPreviewModal";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { FunSpinner } from "@/components/FunSpinner";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";
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

// A restrained pull from the Ndebele strip's palette, used as a rotating
// per-card left-edge accent so colour carries through the whole grid.
const CARD_ACCENTS = ["#e4322b", "#f5b301", "#2f9bf6", "#1a9e5f", "#ff7a1a"];

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i) | 0;
  return h;
}


function CollegesDirectoryInner() {
  const searchParams = useSearchParams();
  const [colleges, setColleges] = useState<Company[]>([]);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [trending, setTrending] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("South Africa");
  const [shortlistOnly, setShortlistOnly] = useState(false);
  const [shortlistIds, setShortlistIds] = useState<Set<string>>(new Set());
  const [previewCompany, setPreviewCompany] = useState<Company | null>(null);

  useEffect(() => {
    Promise.all([
      // active=true: same fix as the Companies/Universities directories --
      // exclude not-yet-vetted rows from the public listing and its counts.
      api.get<Company[]>("/companies?source_type=COLLEGE&limit=5000&active=true"),
      api.get<Vacancy[]>("/vacancies?is_open=true&limit=5000").catch(() => [] as Vacancy[]),
    ]).then(([colls, vacs]) => {
      setColleges(colls);
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

  // Deep link from a "Share" button elsewhere (?company=<id>), or from the
  // Coverage map (?country=<name>): jump straight to that view.
  useEffect(() => {
    const wanted = searchParams.get("company");
    const wantedCountry = searchParams.get("country");
    if (wanted && colleges.length) {
      const found = colleges.find((c) => c.id === wanted);
      if (found) {
        setCountry(found.country || "South Africa");
        setQ(found.company_name);
        return;
      }
    }
    if (wantedCountry) {
      setCountry(wantedCountry);
      setShortlistOnly(false);
    }
  }, [searchParams, colleges]);

  // Real open-position counts per college, from the same vacancy data the
  // Find Jobs page uses -- never fabricated.
  const jobsByCollege = useMemo(() => {
    const m: Record<string, number> = {};
    for (const v of vacancies) m[v.company_id] = (m[v.company_id] || 0) + 1;
    return m;
  }, [vacancies]);

  const countries = useMemo(() => {
    const set = Array.from(new Set(colleges.map((c) => c.country).filter(Boolean) as string[]));
    set.sort((a, b) => (a === "South Africa" ? -1 : b === "South Africa" ? 1 : a.localeCompare(b)));
    return set;
  }, [colleges]);

  const countryCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of colleges) {
      const k = c.country || "";
      if (k) m[k] = (m[k] || 0) + 1;
    }
    return m;
  }, [colleges]);

  const shownColleges = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = colleges
      .filter((c) => shortlistOnly || (c.country || "") === country)
      .filter((c) => !shortlistOnly || shortlistIds.has(c.id))
      .filter((c) => !needle || c.company_name.toLowerCase().includes(needle));
    return [...filtered].sort((a, b) => a.company_name.localeCompare(b.company_name));
  }, [colleges, q, country, jobsByCollege, shortlistOnly, shortlistIds]);

  function surpriseMe() {
    if (!colleges.length) return;
    const withLinks = colleges.filter((c) => c.careers_url);
    const pool = withLinks.length ? withLinks : colleges;
    const pick = pool[Math.floor(Math.random() * pool.length)];
    setShortlistOnly(false);
    setQ("");
    setCountry(pick.country || "South Africa");
    setPreviewCompany(pick);
  }

  const withLinks = colleges.filter((c) => c.careers_url).length;
  const flag = COUNTRY_FLAGS[country] || "🌍";
  const countryTotal = countryCounts[country] ?? 0;
  const countryWithLinks = colleges.filter((c) => (c.country || "") === country && c.careers_url).length;

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!colleges.length) return <FunSpinner label="Loading colleges…" />;

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
          <NdebeleStrip id="colleges-hero-top" palette="vivid" />
          <Banner
            variant="companies"
            eyebrow="Direct to institutions"
            title="College vacancies"
            subtitle={
              <>
                Browse technical and vocational college openings and apply on each institution&apos;s own careers page.{" "}
                <strong className="text-white"><AnimatedNumber value={colleges.length} /></strong> colleges ·{" "}
                <strong className="text-white"><AnimatedNumber value={withLinks} /></strong> with direct careers links.
              </>
            }
          >
            <Button variant="secondary" onClick={surpriseMe}>🎲 Surprise me</Button>
          </Banner>
          <NdebeleStrip id="colleges-hero-bottom" palette="vivid" flip />
        </div>

        <div className="flex items-center gap-4 rounded-2xl border border-ss-border bg-ss-glass px-5 py-4 shadow-sm backdrop-blur-sm">
          <span className="text-5xl leading-none drop-shadow-sm">{flag}</span>
          <div>
            <div className="text-xl font-extrabold text-ss-text">{country}</div>
            <div className="text-sm text-ss-muted">
              <strong className="text-ss-text"><AnimatedNumber value={countryTotal} /></strong> colleges ·{" "}
              <strong className="text-ss-text"><AnimatedNumber value={countryWithLinks} /></strong> with direct careers links
            </div>
          </div>
        </div>

        <Card>
          {countries.length > 1 && (
            <div className="mb-3 flex flex-wrap gap-1.5 border-b border-ss-border pb-3">
              {countries.map((cn) => {
                const active = !shortlistOnly && country === cn;
                return (
                  <button
                    key={cn}
                    onClick={() => { setShortlistOnly(false); setCountry(cn); }}
                    className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                      active ? "bg-navy text-white shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"
                    }`}
                  >
                    <span>{COUNTRY_FLAGS[cn] || "🌍"} {cn}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${
                      active ? "bg-white/20 text-white" : "bg-ss-surface text-ss-muted"
                    }`}>{countryCounts[cn] ?? 0}</span>
                  </button>
                );
              })}
              <button
                onClick={() => setShortlistOnly((v) => !v)}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                  shortlistOnly ? "bg-gold text-white shadow-sm" : "bg-ss-border text-ss-muted hover:bg-ss-primary-soft hover:text-ss-text"
                }`}
              >
                ⭐ My shortlist
                <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${
                  shortlistOnly ? "bg-white/20 text-white" : "bg-ss-surface text-ss-muted"
                }`}>{shortlistIds.size}</span>
              </button>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-[14rem] flex-1">
              <Input
                placeholder="Search college…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
          </div>
        </Card>

        <p className="text-sm text-ss-muted">
          Showing <strong className="text-ss-text">{shownColleges.length}</strong> of{" "}
          {shortlistOnly ? shortlistIds.size : countryTotal} {shortlistOnly ? "shortlisted colleges" : `colleges in ${country}`}.
        </p>

        <div className="grid gap-3 md:grid-cols-2">
          {shownColleges.map((c) => {
            const openJobs = jobsByCollege[c.id] || 0;
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
                      name={c.company_name}
                      website={c.official_website}
                      careersUrl={c.careers_url}
                      country={c.country}
                      gradient={AVATAR_GRADIENTS[Math.abs(hashCode(c.id)) % AVATAR_GRADIENTS.length]}
                    />
                    <div>
                      <div className="font-semibold text-ss-text">{c.company_name}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className="rounded-full bg-teal/10 px-2 py-0.5 text-xs font-semibold text-teal">🏫 College</span>
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
                        {`${openJobs} open position${openJobs === 1 ? "" : "s"}`}
                      </span>
                      <span className="text-ss-border">·</span>
                    </>
                  )}
                  <span className={c.careers_url ? "font-semibold text-brand-dark" : "text-ss-muted"}>
                    {c.careers_url ? "Direct careers link active ✓" : "No careers page yet"}
                  </span>
                </div>

                <div className="mt-3" onClick={(e) => e.stopPropagation()}>
                  {c.careers_url ? (
                    <a href={c.careers_url} target="_blank" rel="noopener noreferrer">
                      <Button>View vacancies →</Button>
                    </a>
                  ) : (
                    <span className="whitespace-nowrap text-xs text-ss-muted">No careers page yet</span>
                  )}
                </div>

                <div onClick={(e) => e.stopPropagation()}>
                  <CompanyActionsRow company={c} shareBasePath="/colleges" />
                </div>
              </div>
            );
          })}
          {shownColleges.length === 0 && (
            <div className="md:col-span-2">
              <EmptyState
                icon={shortlistOnly ? "⭐" : "🔍"}
                title={shortlistOnly ? "Your shortlist is empty" : "No colleges found"}
                message={shortlistOnly ? "Tap the ☆ on any card to add one." : "No colleges match your search."}
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
          openJobs={jobsByCollege[previewCompany.id] || 0}
          shareBasePath="/colleges"
          onClose={() => setPreviewCompany(null)}
        />
      )}
    </div>
  );
}

export default function CollegesDirectoryPage() {
  return (
    <Guard>
      <Suspense fallback={<Spinner label="Loading colleges…" />}>
        <CollegesDirectoryInner />
      </Suspense>
    </Guard>
  );
}
