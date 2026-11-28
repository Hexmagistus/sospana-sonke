"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Search and filter for /opportunities-today. The page is fully server-rendered; this only
 * hides rows that do not match (keyword, category, province), so it works offline and without
 * the backend. Filters are kept in the URL (?q=&cat=&prov=) so a filtered list can be shared.
 */
export default function OpportunityFilter({
  categories,
  provinces,
  total,
}: {
  categories: string[];
  provinces: { code: string; name: string }[];
  total: number;
}) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [prov, setProv] = useState("");
  const [shown, setShown] = useState(total);
  const ready = useRef(false);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    setQ(p.get("q") ?? "");
    setCat(p.get("cat") ?? "");
    setProv(p.get("prov") ?? "");
    ready.current = true;
  }, []);

  useEffect(() => {
    const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const active = words.length > 0 || cat !== "" || prov !== "";
    let n = 0;
    document.querySelectorAll<HTMLElement>("[data-opp]").forEach((li) => {
      const ok =
        (!cat || li.dataset.cat === cat) &&
        (!prov || li.dataset.prov === prov) &&
        words.every((w) => (li.dataset.q ?? "").includes(w));
      li.hidden = !ok;
      if (ok) n += 1;
    });
    document.querySelectorAll<HTMLDetailsElement>("details[data-opp-group]").forEach((d) => {
      const any = d.querySelector("[data-opp]:not([hidden])") !== null;
      d.hidden = !any;
      if (active && any) d.open = true;
    });
    document.querySelectorAll<HTMLElement>("[data-opp-section]").forEach((s) => {
      s.hidden = s.querySelector("details[data-opp-group]:not([hidden])") === null;
    });
    setShown(n);
    if (ready.current) {
      const p = new URLSearchParams();
      if (q.trim()) p.set("q", q.trim());
      if (cat) p.set("cat", cat);
      if (prov) p.set("prov", prov);
      const qs = p.toString();
      window.history.replaceState(null, "", `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash}`);
    }
  }, [q, cat, prov]);

  const field = "w-full rounded-xl border border-[#1F2328]/20 bg-white px-3 py-2.5 text-base text-[#1F2328] shadow-inner focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#0B6575]";

  return (
    <section role="search" aria-label="Search opportunities" className="mb-8 block rounded-2xl border border-white/80 bg-white/90 p-4 shadow-[0_18px_36px_-24px_rgba(31,35,40,0.35)] sm:p-5">
      <h2 className="text-lg font-bold tracking-tight">🔎 Search these posts</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <label className="block text-sm font-semibold">
          Keyword
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. engineer, intern, Eskom" className={`mt-1 ${field}`} />
        </label>
        <label className="block text-sm font-semibold">
          Category
          <select value={cat} onChange={(e) => setCat(e.target.value)} className={`mt-1 ${field}`}>
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          Province
          <select value={prov} onChange={(e) => setProv(e.target.value)} className={`mt-1 ${field}`}>
            <option value="">All provinces</option>
            {provinces.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
          </select>
        </label>
      </div>
      <p className="mt-3 text-sm text-slate-700" aria-live="polite">
        Showing <strong>{shown}</strong> of {total} posts.
        {(q || cat || prov) && (
          <button type="button" onClick={() => { setQ(""); setCat(""); setProv(""); }} className="ml-2 font-semibold text-[#0B6575] underline">
            Clear filters
          </button>
        )}
      </p>
      <p className="mt-1 text-xs text-slate-600">Province is read from the location the employer gives; posts with no clear province only show under &ldquo;All provinces&rdquo;.</p>
    </section>
  );
}
