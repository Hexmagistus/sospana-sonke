"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Input, Button, Badge, Spinner, Alert } from "@/components/ui";
import type { Company } from "@/lib/types";

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
      <div>
        <h1 className="text-2xl font-bold">Companies &amp; opportunities</h1>
        <p className="text-sm text-gray-500">
          Browse every employer in our database and go straight to their official careers page to apply.{" "}
          {companies.length} companies · {withLinks} with direct careers links.
        </p>
      </div>

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
                className={`rounded-md px-3 py-1.5 text-sm whitespace-nowrap ${
                  filter === f ? "bg-brand text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
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
        {shown.map((c) => (
          <Card key={c.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-semibold">{c.company_name}</div>
                <div className="mt-1 flex flex-wrap items-center gap-1">
                  <Badge>{(c.source_type || "").toUpperCase() === "SOE" ? "State-owned" : "JSE-listed"}</Badge>
                  {c.jse_code && <Badge>{c.jse_code}</Badge>}
                  {c.country && <span className="text-xs text-gray-400">{c.country}</span>}
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                {c.careers_url ? (
                  <a href={c.careers_url} target="_blank" rel="noopener noreferrer">
                    <Button variant="ghost">View jobs →</Button>
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
        ))}
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
