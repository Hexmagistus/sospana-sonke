"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Spinner, Alert } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { CompanyLogo } from "@/components/CompanyLogo";
import type { Company } from "@/lib/types";

interface Vacancy {
  id: string;
  company_id: string;
  title: string;
  location: string | null;
  work_mode: string | null;
  employment_type: string | null;
  closing_date: string | null;
  application_url: string | null;
  source_url: string | null;
}

const POPULAR = ["Driver", "Administrator", "Accountant", "Engineer", "Cleaner", "Cashier", "Manager", "Internship", "Learnership"];
const GRAD = ["from-sky to-purple", "from-brand to-brand-dark", "from-gold to-coral", "from-purple to-sky", "from-coral to-gold", "from-navy to-brand"];

function JobsInner() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [jobs, setJobs] = useState<Vacancy[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<Company[]>("/companies?limit=1000").then(setCompanies).catch(() => {});
    search("");   // load all open vacancies by default (browse mode)
  }, []);

  const cmap = useMemo(() => {
    const m = new Map<string, Company>();
    companies.forEach((c) => m.set(c.id, c));
    return m;
  }, [companies]);

  async function search(term: string) {
    const t = term.trim();
    setBusy(true);
    setErr("");
    setSubmitted(t);
    try {
      const qs = t ? `&q=${encodeURIComponent(t)}` : "";
      const r = await api.get<Vacancy[]>(`/vacancies?is_open=true&limit=500${qs}`);
      setJobs(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Search failed");
      setJobs(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Banner
        variant="jobs"
        eyebrow="One search, every employer"
        title="Find jobs by title"
        subtitle="Type a role — like driver, accountant or engineer — and see matching openings across all the employers we track, in one place."
      />

      <Card>
        <form onSubmit={(e) => { e.preventDefault(); search(q); }} className="flex flex-wrap items-center gap-2">
          <div className="min-w-[16rem] flex-1">
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a job title, e.g. driver" />
          </div>
          <Button type="submit">Search jobs</Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {POPULAR.map((p) => (
            <button
              key={p}
              onClick={() => { setQ(p); search(p); }}
              className="rounded-full bg-brand/10 px-3 py-1 text-xs font-semibold text-brand-dark transition hover:bg-brand/20"
            >
              {p}
            </button>
          ))}
        </div>
      </Card>

      {err && <Alert kind="error">{err}</Alert>}
      {busy && <Spinner />}

      {!busy && jobs !== null && (
        <>
          <div className="grid gap-3">
            {jobs.map((j, i) => {
              const c = cmap.get(j.company_id);
              const apply = j.application_url || j.source_url || c?.careers_url || undefined;
              return (
                <Card key={j.id} className="hover:-translate-y-0.5 hover:shadow-md">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <CompanyLogo name={c?.company_name || "?"} website={c?.official_website} careersUrl={c?.careers_url} gradient={GRAD[i % GRAD.length]} />
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
          </div>
          {jobs.length === 0 && (
            <Card accent="gold">
              <p className="font-semibold text-navy">
                {submitted ? `No “${submitted}” openings in our collected vacancies yet.` : "No vacancies collected yet."}
              </p>
              <p className="mt-1 text-sm text-gray-600">
                We gather vacancies from employers&apos; official pages, and coverage is still growing. In the meantime you can browse
                employers directly, or tailor a CV for this role and apply on their careers page.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link href="/companies"><Button variant="ghost">Browse companies</Button></Link>
                <Link href={`/tailor?title=${encodeURIComponent(submitted)}`}><Button>Tailor a CV for “{submitted}”</Button></Link>
              </div>
            </Card>
          )}
        </>
      )}

      {!busy && jobs === null && !err && <Spinner />}
    </div>
  );
}

export default function JobsPage() {
  return (
    <Guard>
      <JobsInner />
    </Guard>
  );
}
