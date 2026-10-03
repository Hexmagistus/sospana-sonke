"use client";

import dynamic from "next/dynamic";
import { useEffect, useId, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { CountrySidebar } from "@/lib/explorer/CountrySidebar";
import { CategorySelect, type CategoryOption } from "@/lib/explorer/CategorySelect";
import { SidebarResizer } from "@/lib/explorer/SidebarResizer";
import { SIDEBAR_DEFAULT, readStoredWidth, storeWidth } from "@/lib/explorer/sidebarWidth";
import { regionLabel, type CountryRow } from "@/lib/countryExplorer";
import { countryFlag } from "@/lib/countryCodes";

// The map (about 125 KB of country outlines) loads only when this view is on screen.
const ExplorerMap = dynamic(() => import("@/components/ExplorerMap"), {
  ssr: false,
  loading: () => (
    <div className="flex aspect-[960/500] w-full items-center justify-center rounded-2xl border border-white/10 bg-[#071528] text-sm text-blue-200">
      Loading the map…
    </div>
  ),
});

export type ExplorerStats = {
  employers: number;
  withLinks: number;
  counted: number;
  openVacancies: number;
};

type Props = {
  rows: readonly CountryRow[];
  selected: string;
  onSelect: (name: string) => void;
  stats: ExplorerStats | null;
  /** "employers", "universities", "hospitals". */
  noun?: string;
  /** One category dropdown above the map. Omit to hide it (universities, hospitals). */
  categories?: readonly CategoryOption[];
  selectedCategory?: string;
  onSelectCategory?: (id: string) => void;
  allowAll?: boolean;
  /** Label of the "view" button and where it goes. */
  viewLabel?: string;
  onView?: () => void;
  /** Shown when All countries is picked in a view that cannot list everything at once. */
  allHint?: ReactNode;
};

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-white/10 bg-white/5 px-3 py-2">
      <div className="text-[10px] font-bold uppercase tracking-wider text-blue-200">{label}</div>
      <div className="text-lg font-extrabold tabular-nums text-white">{value}</div>
      {sub && <div className="text-[11px] text-blue-200">{sub}</div>}
    </div>
  );
}

/** Split view: country list on the left, big map, header and stats strip on the right. */
export function CountryExplorer({
  rows, selected, onSelect, stats, noun = "employers", categories, selectedCategory,
  onSelectCategory, allowAll = true, viewLabel, onView, allHint,
}: Props) {
  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of rows) if (r.employers > 0) m[r.name] = r.employers;
    return m;
  }, [rows]);
  const row = rows.find((r) => r.name === selected) ?? null;
  const flag = selected ? countryFlag(selected) : "🌍";
  const title = selected || "All countries";
  const sub = selected ? regionLabel(selected) : `${rows.filter((r) => r.selectable).length} countries with ${noun}`;
  const cap = noun.charAt(0).toUpperCase() + noun.slice(1);

  // Sidebar width: the default on the server and first paint, then the saved one.
  const [sbw, setSbw] = useState(SIDEBAR_DEFAULT);
  const splitRef = useRef<HTMLDivElement | null>(null);
  const sidebarId = useId();
  useEffect(() => { setSbw(readStoredWidth()); }, []);
  function resize(px: number, persist: boolean) {
    setSbw(px);
    if (persist) storeWidth(px);
  }

  return (
    <section
      aria-label={`Browse ${noun} by country`}
      className="overflow-hidden rounded-2xl border border-[#1d3a63] bg-[#0a1a30] text-white shadow-lg"
    >
      <div
        ref={splitRef}
        style={{ "--sbw": `${sbw}px` } as CSSProperties}
        className="grid lg:grid-cols-[var(--sbw)_auto_minmax(0,1fr)]"
      >
        <div id={sidebarId} className="order-2 min-w-0 border-t border-white/10 p-3 lg:order-1 lg:max-h-[46rem] lg:border-t-0">
          <CountrySidebar
            rows={rows}
            selected={selected}
            onSelect={onSelect}
            noun={noun}
            allowAll={allowAll}
          />
        </div>

        <div className="hidden lg:order-2 lg:flex">
          <SidebarResizer width={sbw} onChange={resize} containerRef={splitRef} controls={sidebarId} />
        </div>

        <div className="order-1 min-w-0 p-3 sm:p-4 lg:order-3">
          <header className="flex flex-col items-center gap-1 pb-3 text-center" aria-live="polite">
            <span aria-hidden className="text-6xl leading-none drop-shadow-lg">{flag}</span>
            <h2 className="text-2xl font-extrabold text-white sm:text-3xl">{title}</h2>
            <p className="text-sm text-blue-200">{sub}</p>
            <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
              {onView && (
                <button
                  type="button"
                  onClick={onView}
                  className="rounded-full bg-gold px-4 py-1.5 text-sm font-bold text-navy shadow hover:brightness-110"
                >
                  {viewLabel ?? `View all ${noun}`}
                </button>
              )}
              {allowAll && (
                <button
                  type="button"
                  onClick={() => onSelect("")}
                  disabled={!selected}
                  className="rounded-full border border-white/25 px-4 py-1.5 text-sm font-semibold text-white hover:bg-white/10 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent"
                >
                  Clear selection
                </button>
              )}
            </div>
          </header>

          {categories && categories.length > 0 && onSelectCategory && (
            <CategorySelect
              options={categories}
              value={selectedCategory ?? "all"}
              onChange={onSelectCategory}
              scope={selected || "all countries"}
            />
          )}

          <ExplorerMap counts={counts} selected={selected} onSelect={onSelect} noun={noun} />

          {selected && row && !row.selectable && (
            <p className="mt-2 text-sm text-blue-200">No {noun} yet in {selected}.</p>
          )}
          {!selected && allHint && <p className="mt-2 text-sm text-blue-200">{allHint}</p>}

          {stats && (
            <dl aria-label={`${selected || "All countries"} figures`} className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label={cap} value={stats.employers.toLocaleString()} />
              <Stat label="Direct link" value={stats.withLinks.toLocaleString()} sub="straight to their jobs page" />
              <Stat label="Counted" value={stats.counted.toLocaleString()} sub={`of ${stats.employers.toLocaleString()}; the rest say “Not counted yet”`} />
              <Stat label="Open vacancies held" value={stats.openVacancies.toLocaleString()} sub="rows we hold, not a promise" />
            </dl>
          )}
        </div>
      </div>
    </section>
  );
}
