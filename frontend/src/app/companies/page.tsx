"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Spinner, Alert } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import type { Company } from "@/lib/types";

interface Vacancy {
  id: string;
  company_id: string;
  title: string;
  location: string | null;
  employment_type: string | null;
  closing_date: string | null;
  application_url: string | null;
  source_url: string | null;
}

type Accent = "sky" | "teal" | "gold" | "purple" | "coral" | "navy";
const ACCENTS: Accent[] = ["sky", "teal", "gold", "purple", "coral", "navy"];
const AVATAR_GRADIENTS = [
  "from-sky to-purple",
  "from-brand to-brand-dark",
  "from-gold to-coral",
  "from-purple to-sky",
  "from-coral to-gold",
  "from-navy to-brand",
];

function CompaniesDirectoryInner() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [vacancies, setVacancies] = useState<Vacancy[] | null>(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<"companies" | "jobs">("companies");
  const [filter, setFilter] = useState<"all" | "JSE" | "SOE">("all");
  const [country, setCountry] = useState("South Africa");

  useEffect(() => {
    api.get<Company[]>("/companies?limit=1000").then(setCompanies).catch((e) => setErr(e.message));
    api.get<Vacancy[]>("/vacancies?is_open=true&limit=1000").then(setVacancies).catch(() => setVacancies([]));
  }, []);

  const cmap = useMemo(() => {
    const m = new Map<string, Company>();
    companies.forEach((c) => m.set(c.id, c));
    return m;
  }, [companies]);

  const COUNTRY_FLAGS: Record<string, string> = {
    "South Africa": "🇿🇦", "Lesotho": "🇱🇸", "Botswana": "🇧🇼", "Namibia": "🇳🇦",
    "Eswatini": "🇸🇿", "Zimbabwe": "🇿🇼", "Mozambique": "🇲🇿",
  };
  const countries = useMemo(() => {
    const set = Array.from(new Set(companies.map((c) => c.country).filter(Boolean) as string[]));
    set.sort((a, b) => (a === "South Africa" ? -1 : b === "South Africa" ? 1 : a.localeCompare(b)));
    return set;
  }, [companies]);

  const shownCompanies = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return companies
      .filter((c) => (c.country || "") === country)
      .filter((c) => filter === "all" || (c.source_type || "").toUpperCase() === filter)
      .filter((c) => !needle
        || c.company_name.toLowerCase().includes(needle)
        || (c.jse_code || "").toLowerCase().includes(needle))
      .sort((a, b) => a.company_name.localeCompare(b.company_name));
  }, [companies, q, filter]);

  const shownJobs = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (vacancies || [])
      .filter((v) => (cmap.get(v.company_id)?.country || "") === country)
      .filter((v) => !needle || v.title.toLowerCase().includes(needle))
      .sort((a, b) => a.title.localeCompare(b.title));
  }, [vacancies, q, cmap, country]);

  const withLinks = companies.filter((c) => c.careers_url).length;

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!companies.length) return <Spinner />;

  return (
    <div className="space-y-6">
      <Banner
        variant="companies"
        eyebrow="Direct to employers"
        title="Companies & opportunities"
        subtitle={
          <>
            Search jobs by title across every employer, or browse the full directory and apply on their official careers
            page. <strong className="text-white">{companies.length}</strong> companies ·{" "}
            <strong className="text-white">{withLinks}</strong> with direct careers links.
          </>
        }
      />

      <Card>
        {countries.length > 1 && (
          <div className="mb-3 flex flex-wrap gap-1 border-b border-gray-100 pb-3">
            {countries.map((cn) => (
              <button
                key={cn}
                onClick={() => setCountry(cn)}
                className={`rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                  country === cn ? "bg-navy text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {COUNTRY_FLAGS[cn] || "🌍"} {cn}
              </button>
            ))}
          </div>
        )}
        <div className="mb-3 flex gap-1">
          <button
            onClick={() => setMode("companies")}
            className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
              mode === "companies" ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            Browse companies
          </button>
          <button
            onClick={() => setMode("jobs")}
            className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
              mode === "jobs" ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            Search jobs
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="min-w-[14rem] flex-1">
            <Input
              placeholder={mode === "jobs" ? "Search a job title, e.g. driver — or leave blank for all jobs" : "Search company or JSE code…"}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          {mode === "companies" && (
            <div className="flex gap-1">
              {(["all", "JSE", "SOE"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition ${
                    filter === f ? "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {f === "all" ? "All" : f}
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      {mode === "companies" && (
        <div className="grid gap-3 md:grid-cols-2">
          {shownCompanies.map((c, i) => {
            const isSOE = (c.source_type || "").toUpperCase() === "SOE";
            return (
              <Card key={c.id} accent={ACCENTS[i % ACCENTS.length]} className="hover:-translate-y-0.5 hover:shadow-md">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <CompanyLogo name={c.company_name} website={c.official_website} careersUrl={c.careers_url} gradient={AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]} />
                    <div>
                      <div className="font-semibold text-navy">{c.company_name}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${isSOE ? "bg-purple/10 text-purple" : "bg-brand/10 text-brand-dark"}`}>
                          {isSOE ? "State-owned" : "JSE-listed"}
                        </span>
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
                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    {c.careers_url ? (
                      <a href={c.careers_url} target="_blank" rel="noopener noreferrer">
                        <Button>View jobs →</Button>
                      </a>
                    ) : (
                      <span className="whitespace-nowrap text-xs text-gray-400">No careers page yet</span>
                    )}
                    <Link href={`/tailor?company=${encodeURIComponent(c.company_name)}`}>
                      <Button variant="ghost">Tailor CV</Button>
                    </Link>
                  </div>
                </div>
              </Card>
            );
          })}
          {shownCompanies.length === 0 && <p className="text-sm text-gray-400">No companies match your search.</p>}
        </div>
      )}

      {mode === "jobs" && (
        vacancies === null ? <Spinner /> : (
          <div className="grid gap-3">
            {shownJobs.map((j, i) => {
              const c = cmap.get(j.company_id);
              const apply = j.application_url || j.source_url || c?.careers_url || undefined;
              return (
                <Card key={j.id} className="hover:-translate-y-0.5 hover:shadow-md">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <CompanyLogo name={c?.company_name || "?"} website={c?.official_website} careersUrl={c?.careers_url} gradient={AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]} />
                      <div>
                        <div className="font-semibold text-navy">{j.title}</div>
                        <div className="text-sm text-gray-600">{c?.company_name || "Employer"}</div>
                        <div className="mt-1 flex flex-wrap items-center gap-1 text-xs">
                          {j.location && <span className="rounded-full bg-sky/10 px-2 py-0.5 font-semibold text-sky">{j.location}</span>}
                          {j.employment_type && <span className="rounded-full bg-purple/10 px-2 py-0.5 font-semibold text-purple">{j.employment_type}</span>}
                          {j.closing_date && <span className="text-gray-400">Closes {j.closing_date}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1.5">
                      {apply && (
                        <a href={apply} target="_blank" rel="noopener noreferrer">
                          <Button>Apply →</Button>
                        </a>
                      )}
                      <Link href={`/tailor?company=${encodeURIComponent(c?.company_name || "")}&title=${encodeURIComponent(j.title)}`}>
                        <Button variant="ghost">Tailor CV</Button>
                      </Link>
                    </div>
                  </div>
                </Card>
              );
            })}
            {shownJobs.length === 0 && (
              <Card accent="gold">
                <p className="font-semibold text-navy">No matching jobs in our collected vacancies yet.</p>
                <p className="mt-1 text-sm text-gray-600">
                  Coverage is still growing. Try a broader title, browse companies directly, or tailor a CV and apply on
                  the employer&apos;s careers page.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={() => setMode("companies")} className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:border-brand hover:text-brand-dark">Browse companies</button>
                  <Link href={`/tailor?title=${encodeURIComponent(q.trim())}`}><Button>Tailor a CV</Button></Link>
                </div>
              </Card>
            )}
          </div>
        )
      )}
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
