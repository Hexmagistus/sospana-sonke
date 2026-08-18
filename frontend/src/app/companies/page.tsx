"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Spinner, Alert } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { CompanyLogo, isAtsPortal } from "@/components/CompanyLogo";
import type { Company } from "@/lib/types";

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
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<"all" | "JSE" | "SOE">("all");

  useEffect(() => {
    api.get<Company[]>("/companies?limit=1000").then(setCompanies).catch((e) => setErr(e.message));
  }, []);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return companies
      .filter((c) => filter === "all" || (c.source_type || "").toUpperCase() === filter)
      .filter((c) => !needle
        || c.company_name.toLowerCase().includes(needle)
        || (c.jse_code || "").toLowerCase().includes(needle))
      .sort((a, b) => a.company_name.localeCompare(b.company_name));
  }, [companies, q, filter]);

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
            Browse every employer in our database and go straight to their official careers page to apply.{" "}
            <strong className="text-white">{companies.length}</strong> companies ·{" "}
            <strong className="text-white">{withLinks}</strong> with direct careers links.
          </>
        }
      />

      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <div className="min-w-[14rem] flex-1">
            <Input placeholder="Search company or JSE code…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
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
        </div>
      </Card>

      <p className="text-xs text-gray-500">{shown.length} shown</p>

      <div className="grid gap-3 md:grid-cols-2">
        {shown.map((c, i) => {
          const isSOE = (c.source_type || "").toUpperCase() === "SOE";
          return (
            <Card key={c.id} accent={ACCENTS[i % ACCENTS.length]} className="hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <CompanyLogo
                    name={c.company_name}
                    website={c.official_website}
                    careersUrl={c.careers_url}
                    gradient={AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]}
                  />
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
        {shown.length === 0 && <p className="text-sm text-gray-400">No companies match your search.</p>}
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
