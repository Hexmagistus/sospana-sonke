"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

/** One directory row from public/company-index.json (built by scripts/build_company_index.py). */
type Company = { n: string; c: string; k: string; u: string; p?: number; a?: string };

const ALL = "";
const SA = "South Africa";

/**
 * Company dropdown: every employer in the directory, alphabetical, grouped by country
 * (South Africa first) or by category inside one country. Reads a static file, so it
 * keeps working when the database/API is offline. A native <select> keeps it easy on phones.
 */
export default function CompanyPicker({ className = "" }: { className?: string }) {
  const [rows, setRows] = useState<Company[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [country, setCountry] = useState<string>(SA);
  const [filter, setFilter] = useState("");
  const [picked, setPicked] = useState<Company | null>(null);

  useEffect(() => {
    let live = true;
    fetch("/company-index.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { companies: Company[] }) => live && setRows(d.companies))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  const countries = useMemo(() => {
    const set = new Set((rows ?? []).map((r) => r.c));
    set.delete(SA);
    return [SA, ...Array.from(set).sort((a, b) => a.localeCompare(b))];
  }, [rows]);

  const groups = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = (rows ?? []).filter((r) => (country === ALL || r.c === country) && (!q || r.n.toLowerCase().includes(q)));
    const key = (r: Company) => (country === ALL ? r.c : r.k);
    const map = new Map<string, Company[]>();
    for (const r of list) {
      const k = key(r);
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(r);
    }
    const names = Array.from(map.keys()).sort((a, b) => (a === SA ? -1 : b === SA ? 1 : a.localeCompare(b)));
    return names.map((g) => ({ label: g, items: map.get(g)!.sort((a, b) => a.n.localeCompare(b.n)) }));
  }, [rows, country, filter]);

  const total = groups.reduce((n, g) => n + g.items.length, 0);
  const id = (r: Company) => `${r.c}|${r.n}`;

  return (
    <div className={`rounded-2xl border border-[#E2AE3C]/60 bg-[#FFF8EC] p-4 text-[#1F2328] shadow-sm sm:p-5 ${className}`}>
      <h2 className="text-lg font-bold tracking-tight sm:text-xl">🏢 Find a company&apos;s careers page</h2>
      <p className="mt-1 text-sm text-[#3f4a5c]">
        Pick any employer in our directory{rows ? ` (${rows.length.toLocaleString("en-ZA")} companies)` : ""}. We take you to its own careers page. Free, no login.
      </p>
      {failed && (
        <p className="mt-3 text-sm font-semibold text-[#9A3722]">
          The company list did not load. Check your connection, or open the{" "}
          <Link href="/sa-careers" className="underline">SA careers pages</Link>.
        </p>
      )}
      <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
        <label className="block text-sm font-semibold">
          Country
          <select
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
              setPicked(null);
            }}
            disabled={!rows}
            className="mt-1 block min-h-11 w-full rounded-lg border border-[#1F2328]/25 bg-white px-3 text-base text-[#1F2328]"
          >
            <option value={ALL}>All countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          Narrow the list (optional)
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Type part of a name, e.g. Eskom"
            disabled={!rows}
            className="mt-1 block min-h-11 w-full rounded-lg border border-[#1F2328]/25 bg-white px-3 text-base text-[#1F2328] placeholder:text-[#5b6472]"
          />
        </label>
      </div>
      <label className="mt-3 block text-sm font-semibold">
        Company {rows && <span className="font-normal text-[#3f4a5c]">({total.toLocaleString("en-ZA")} shown)</span>}
        <select
          value={picked ? id(picked) : ""}
          onChange={(e) => {
            const v = e.target.value;
            setPicked(groups.flatMap((g) => g.items).find((r) => id(r) === v) ?? null);
          }}
          disabled={!rows || total === 0}
          className="mt-1 block min-h-11 w-full rounded-lg border-2 border-[#FD6948] bg-white px-3 text-base text-[#1F2328]"
        >
          <option value="">{!rows ? "Loading companies…" : total ? "Choose a company…" : "No company matches"}</option>
          {groups.map((g) => (
            <optgroup key={g.label} label={g.label}>
              {g.items.map((r) => (
                <option key={id(r)} value={id(r)}>
                  {r.n}{r.p ? ` · ${r.p} open` : ""}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      {picked && (
        <div className="mt-4 rounded-xl border border-[#1F2328]/15 bg-white p-4" aria-live="polite">
          <p className="text-base font-bold">{picked.n}</p>
          <p className="text-sm text-[#3f4a5c]">{picked.c} · {picked.k}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <a
              href={picked.u}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-11 items-center rounded-lg bg-[#B8432A] px-4 text-base font-semibold text-white hover:bg-[#9A3722]"
            >
              Open careers page ↗
            </a>
            {picked.p && picked.a ? (
              <Link
                href={`/opportunities-today#${picked.a}`}
                className="inline-flex min-h-11 items-center rounded-lg border-2 border-[#05606F] px-4 text-base font-semibold text-[#05606F] hover:bg-[#EAF4FC]"
              >
                See {picked.p} open {picked.p === 1 ? "post" : "posts"} checked today →
              </Link>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
