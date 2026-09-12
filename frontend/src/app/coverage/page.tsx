"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Guard from "@/components/Guard";
import { api } from "@/lib/api";
import { Card, Alert } from "@/components/ui";
import { Banner } from "@/components/Banner";
import { NdebeleStrip } from "@/components/NdebeleStrip";
import { FunSpinner } from "@/components/FunSpinner";
import { AnimatedNumber } from "@/components/AnimatedNumber";
import { COUNTRY_FLAGS } from "@/lib/countryFlags";
import type { CoverageRow } from "@/lib/types";

function CoverageInner() {
  const [rows, setRows] = useState<CoverageRow[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get<CoverageRow[]>("/companies/coverage").then(setRows).catch((e) => setErr(e.message));
  }, []);

  const byCountry = useMemo(() => {
    const m = new Map<string, CoverageRow[]>();
    for (const r of rows) {
      const list = m.get(r.country) || [];
      list.push(r);
      m.set(r.country, list);
    }
    return Array.from(m.entries()).sort(([a], [b]) =>
      a === "South Africa" ? -1 : b === "South Africa" ? 1 : a.localeCompare(b));
  }, [rows]);

  const totals = useMemo(
    () =>
      rows.reduce(
        (acc, r) => ({
          total: acc.total + r.total,
          with_careers_url: acc.with_careers_url + r.with_careers_url,
          verified_ok: acc.verified_ok + r.verified_ok,
          pending_verification: acc.pending_verification + r.pending_verification,
          needs_attention: acc.needs_attention + r.needs_attention,
        }),
        { total: 0, with_careers_url: 0, verified_ok: 0, pending_verification: 0, needs_attention: 0 },
      ),
    [rows],
  );

  if (err) return <Alert kind="error">{err}</Alert>;
  if (!rows.length) return <FunSpinner label="Loading coverage…" />;

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-2xl shadow-sm">
        <NdebeleStrip id="coverage-hero-top" palette="vivid" />
        <Banner
          variant="companies"
          eyebrow="How complete is this, honestly"
          title="Coverage map"
          subtitle={
            <>
              <strong className="text-white"><AnimatedNumber value={totals.verified_ok} /></strong> verified working ·{" "}
              <strong className="text-white"><AnimatedNumber value={totals.pending_verification} /></strong> pending verification ·{" "}
              <strong className="text-white"><AnimatedNumber value={totals.needs_attention} /></strong> need attention — out of{" "}
              <strong className="text-white"><AnimatedNumber value={totals.total} /></strong> entries across every country and category.
            </>
          }
        />
        <NdebeleStrip id="coverage-hero-bottom" palette="vivid" flip />
      </div>

      <Alert kind="info">
        &quot;Verified working&quot; means the URL tester or a scan run has actually loaded the page and it looks
        like a careers page. &quot;Pending verification&quot; rows were added from research but not yet fetched
        live — most new university entries fall here first. This is the same data we use internally to decide
        what to check next, not a marketing number.
      </Alert>

      <Card>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Tap a country to jump straight to its listings
        </h2>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {byCountry.map(([country, list]) => {
            const total = list.reduce((s, r) => s + r.total, 0);
            const verified = list.reduce((s, r) => s + r.verified_ok, 0);
            const ratio = total ? verified / total : 0;
            return (
              <Link
                key={country}
                href={`/companies?country=${encodeURIComponent(country)}`}
                className="flex flex-col items-center gap-1 rounded-xl border border-gray-100 p-2.5 text-center transition hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-md"
                style={{ backgroundColor: `rgba(26,158,95,${0.05 + ratio * 0.25})` }}
                title={`${verified} of ${total} verified working`}
              >
                <span className="text-2xl leading-none">{COUNTRY_FLAGS[country] || "🌍"}</span>
                <span className="text-[11px] font-semibold leading-tight text-navy">{country}</span>
                <span className="text-[10px] tabular-nums text-gray-500">{total}</span>
              </Link>
            );
          })}
        </div>
      </Card>

      {byCountry.map(([country, list]) => (
        <Card key={country}>
          <div className="mb-3 flex items-center gap-2">
            <span className="text-2xl leading-none">{COUNTRY_FLAGS[country] || "🌍"}</span>
            <h2 className="text-lg font-bold text-navy">{country}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs uppercase tracking-wide text-gray-400">
                  <th className="py-1.5 pr-3">Category</th>
                  <th className="py-1.5 pr-3">Total</th>
                  <th className="py-1.5 pr-3">Has link</th>
                  <th className="py-1.5 pr-3">Verified ✓</th>
                  <th className="py-1.5 pr-3">Pending</th>
                  <th className="py-1.5 pr-3">Needs attention</th>
                </tr>
              </thead>
              <tbody>
                {[...list]
                  .sort((a, b) => a.source_type.localeCompare(b.source_type))
                  .map((r) => (
                    <tr key={r.source_type} className="border-b border-gray-50 last:border-0">
                      <td className="py-1.5 pr-3 font-medium text-gray-700">{r.source_type}</td>
                      <td className="py-1.5 pr-3 tabular-nums">{r.total}</td>
                      <td className="py-1.5 pr-3 tabular-nums text-gray-500">{r.with_careers_url}</td>
                      <td className="py-1.5 pr-3 tabular-nums text-brand-dark">{r.verified_ok}</td>
                      <td className="py-1.5 pr-3 tabular-nums text-gray-500">{r.pending_verification}</td>
                      <td className="py-1.5 pr-3 tabular-nums text-coral">{r.needs_attention}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  );
}

export default function CoveragePage() {
  return (
    <Guard>
      <CoverageInner />
    </Guard>
  );
}
