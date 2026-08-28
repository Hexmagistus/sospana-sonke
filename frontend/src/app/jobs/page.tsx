"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Spinner, Alert } from "@/components/ui";
import { Banner } from "@/components/Banner";
import type { Company, Vacancy } from "@/lib/types";

const COUNTRY_FLAGS: Record<string, string> = {
  "South Africa": "🇿🇦", "Lesotho": "🇱🇸", "Botswana": "🇧🇼", "Namibia": "🇳🇦",
  "Eswatini": "🇸🇿", "Zimbabwe": "🇿🇼", "Mozambique": "🇲🇿",
  "Malawi": "🇲🇼", "Mauritius": "🇲🇺", "Zambia": "🇿🇲",
  "Tanzania": "🇹🇿", "Angola": "🇦🇴",
};

type Accent = "sky" | "teal" | "gold" | "purple" | "coral" | "navy";
const ACCENTS: Accent[] = ["sky", "teal", "gold", "purple", "coral", "navy"];

interface EnrichedVacancy extends Vacancy {
  companyName: string;
  country: string;
  careersUrl: string | null;
}

function FindJobsInner() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    (async () => {
      try {
        const [cos, vacs] = await Promise.all([
          api.get<Company[]>("/companies?limit=1000"),
          api.get<Vacancy[]>("/vacancies?is_open=true&limit=500"),
        ]);
        setCompanies(cos);
        setVacancies(vacs);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Could not load vacancies.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const companyMap = useMemo(() => {
    const m = new Map<string, Company>();
    for (const c of companies) m.set(c.id, c);
    return m;
  }, [companies]);

  // All regions we operate in (from the company directory), South Africa first.
  const regions = useMemo(() => {
    const set = Array.from(new Set(companies.map((c) => c.country).filter(Boolean)));
    set.sort((a, b) => (a === "South Africa" ? -1 : b === "South Africa" ? 1 : a.localeCompare(b)));
    return set;
  }, [companies]);

  // Default: every region selected.
  useEffect(() => {
    if (regions.length && selected.size === 0) setSelected(new Set(regions));
  }, [regions]); // eslint-disable-line react-hooks/exhaustive-deps

  const enriched = useMemo<EnrichedVacancy[]>(() => {
    return vacancies
      .map((v) => {
        const c = companyMap.get(v.company_id);
        if (!c) return null;
        return { ...v, companyName: c.company_name, country: c.country, careersUrl: c.careers_url };
      })
      .filter(Boolean) as EnrichedVacancy[];
  }, [vacancies, companyMap]);

  const vacanciesByRegion = useMemo(() => {
    const m: Record<string, number> = {};
    for (const v of enriched) m[v.country] = (m[v.country] || 0) + 1;
    return m;
  }, [enriched]);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return enriched
      .filter((v) => selected.has(v.country))
      .filter((v) => !needle
        || v.title.toLowerCase().includes(needle)
        || v.companyName.toLowerCase().includes(needle)
        || (v.location || "").toLowerCase().includes(needle))
      .sort((a, b) => (b.last_seen_at || "").localeCompare(a.last_seen_at || ""));
  }, [enriched, selected, q]);

  function toggle(region: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(region)) next.delete(region); else next.add(region);
      return next;
    });
  }
  const allOn = selected.size === regions.length && regions.length > 0;

  if (err) return <Alert kind="error">{err}</Alert>;
  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <Banner
        variant="companies"
        eyebrow="Live vacancies"
        title="Find jobs across the region"
        subtitle={
          <>
            Every open vacancy we&apos;ve discovered, pulled together from your selected regions.{" "}
            <strong className="text-white">{enriched.length}</strong> open{" "}
            {enriched.length === 1 ? "vacancy" : "vacancies"} across{" "}
            <strong className="text-white">{Object.keys(vacanciesByRegion).length}</strong>{" "}
            {Object.keys(vacanciesByRegion).length === 1 ? "region" : "regions"}.
          </>
        }
      />

      {/* Unmissable honesty notice */}
      <div className="rounded-2xl border-l-4 border-gold bg-gold/10 p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="text-2xl leading-none">📌</span>
          <div>
            <p className="font-bold text-navy">Heads up — this isn&apos;t every vacancy</p>
            <p className="mt-1 text-sm leading-relaxed text-gray-700">
              What you see here is only a portion of the jobs actually open across the region. Many employers
              protect their careers pages from automated access (their robots and privacy rules), so we simply
              can&apos;t list all of their vacancies here. To be sure you&apos;re not missing anything, open the{" "}
              <Link href="/companies" className="font-semibold text-brand-dark underline">Companies</Link>{" "}
              directory and check each employer&apos;s official careers page one by one — that&apos;s where their
              full, up-to-date list of openings lives.
            </p>
          </div>
        </div>
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Regions</p>
          <button
            onClick={() => setSelected(allOn ? new Set() : new Set(regions))}
            className="text-xs font-semibold text-brand-dark hover:underline"
          >
            {allOn ? "Clear all" : "Select all"}
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {regions.map((r) => {
            const on = selected.has(r);
            const count = vacanciesByRegion[r] || 0;
            return (
              <button
                key={r}
                onClick={() => toggle(r)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                  on ? "bg-navy text-white shadow-sm" : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                }`}
              >
                <span>{COUNTRY_FLAGS[r] || "🌍"} {r}</span>
                <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${
                  on ? "bg-white/20 text-white" : "bg-white text-gray-500"
                }`}>{count}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-4">
          <Input
            placeholder="Search job title, company or location…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </Card>

      {enriched.length === 0 ? (
        <Card>
          <h3 className="font-semibold text-navy">No vacancies discovered yet</h3>
          <p className="mt-1 text-sm text-gray-600">
            We haven&apos;t pulled in live vacancies for these employers yet. In the meantime you can go
            straight to each employer&apos;s official careers page from the Companies directory.
          </p>
          <div className="mt-3">
            <Link href="/companies"><Button>Browse companies →</Button></Link>
          </div>
        </Card>
      ) : (
        <>
          <p className="text-sm text-gray-500">
            Showing <strong className="text-navy">{shown.length}</strong> of {enriched.length} vacancies
            {selected.size < regions.length ? ` in ${selected.size} selected region${selected.size === 1 ? "" : "s"}` : ""}.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {shown.map((v, i) => {
              const applyUrl = v.application_url || v.source_url || v.careersUrl;
              return (
                <Card key={v.id} accent={ACCENTS[i % ACCENTS.length]} className="hover:-translate-y-0.5 hover:shadow-md">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-semibold text-navy">{v.title}</div>
                      <div className="mt-0.5 text-sm text-gray-600">{v.companyName}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className="rounded-full bg-brand/10 px-2 py-0.5 text-xs font-semibold text-brand-dark">
                          {COUNTRY_FLAGS[v.country] || "🌍"} {v.country}
                        </span>
                        {v.location && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{v.location}</span>}
                        {v.work_mode && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{v.work_mode}</span>}
                        {v.employment_type && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{v.employment_type}</span>}
                        {v.closing_date && <span className="rounded-full bg-coral/10 px-2 py-0.5 text-xs font-semibold text-coral">Closes {v.closing_date}</span>}
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1.5">
                      {applyUrl ? (
                        <a href={applyUrl} target="_blank" rel="noopener noreferrer">
                          <Button>Apply →</Button>
                        </a>
                      ) : (
                        <span className="whitespace-nowrap text-xs text-gray-400">No link</span>
                      )}
                      <Link href={`/tailor?company=${encodeURIComponent(v.companyName)}`}>
                        <Button variant="ghost">Tailor CV</Button>
                      </Link>
                    </div>
                  </div>
                </Card>
              );
            })}
            {shown.length === 0 && (
              <p className="text-sm text-gray-400">No vacancies match your regions or search.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function FindJobsPage() {
  return (
    <Guard>
      <FindJobsInner />
    </Guard>
  );
}
