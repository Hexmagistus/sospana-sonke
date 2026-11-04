"use client";

import { useState } from "react";

type Company = { n: string; c: string; k: string; u: string };

/**
 * Compact company dropdown for the header. The static company index is fetched only on
 * first focus, so other pages stay fast, and it works with the backend offline.
 */
export default function HeaderCompanySelect({ className = "" }: { className?: string }) {
  const [groups, setGroups] = useState<{ label: string; items: Company[] }[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    if (groups || loading) return;
    setLoading(true);
    fetch("/company-index.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { companies: Company[] }) => {
        const map = new Map<string, Company[]>();
        for (const r of d.companies) {
          if (r.c !== "South Africa") continue;
          if (!map.has(r.k)) map.set(r.k, []);
          map.get(r.k)!.push(r);
        }
        setGroups(
          [...map.keys()].sort().map((k) => ({ label: k, items: map.get(k)!.sort((a, b) => a.n.localeCompare(b.n)) })),
        );
      })
      .catch(() => setGroups([]))
      .finally(() => setLoading(false));
  };

  return (
    <label className={`relative block ${className}`}>
      <span className="sr-only">Open a South African company&apos;s careers page</span>
      <span aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-sm">🏢</span>
      <select
        defaultValue=""
        onFocus={load}
        onMouseDown={load}
        onTouchStart={load}
        onChange={(e) => {
          const url = e.target.value;
          if (url) window.open(url, "_blank", "noopener,noreferrer");
          e.target.value = "";
        }}
        className="h-9 w-full appearance-none truncate rounded-full border border-[#1F2328]/15 bg-white pl-8 pr-7 text-sm text-[#1F2328] shadow-inner focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#0B6575]"
      >
        <option value="">{loading ? "Loading companies…" : "Find a company…"}</option>
        {groups?.length === 0 && <option disabled>Company list unavailable</option>}
        {groups?.map((g) => (
          <optgroup key={g.label} label={g.label}>
            {g.items.map((c) => (
              <option key={c.n + c.u} value={c.u}>{c.n}</option>
            ))}
          </optgroup>
        ))}
      </select>
      <span aria-hidden="true" className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-[#4A4F57]">▾</span>
    </label>
  );
}
