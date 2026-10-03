"use client";

import dynamic from "next/dynamic";
import { useMemo, type ReactNode } from "react";
import { CountrySidebar, type CategoryItem } from "@/lib/explorer/CountrySidebar";
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
  /** Category breakdown for the shown scope, largest first. */
  categories: { label: string; count: number }[];
};

type Props = {
  rows: readonly CountryRow[];
  selected: string;
  onSelect: (name: string) => void;
  stats: ExplorerStats | null;
  /** "employers", "universities", "hospitals". */
  noun?: string;
  categories?: readonly CategoryItem[];
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

  return (
    <section
      aria-label={`Browse ${noun} by country`}
      className="overflow-hidden rounded-2xl border border-[#1d3a63] bg-[#0a1a30] text-white shadow-lg"
    >
      <div className="grid lg:grid-cols-[19rem_minmax(0,1fr)]">
        <div className="order-2 border-t border-white/10 p-3 lg:order-1 lg:max-h-[46rem] lg:border-r lg:border-t-0">
          <CountrySidebar
            rows={rows}
            selected={selected}
            onSelect={onSelect}
            noun={noun}
            categories={categories}
            selectedCategory={selectedCategory}
            onSelectCategory={onSelectCategory}
            allowAll={allowAll}
          />
        </div>

        <div className="order-1 min-w-0 p-3 sm:p-4 lg:order-2">
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
          {stats && stats.categories.length > 0 && (
            <p className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-blue-200">
              <span className="font-bold uppercase tracking-wider">By category</span>
              {stats.categories.slice(0, 6).map((c) => (
                <span key={c.label} className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 font-semibold text-white">
                  {c.label} <span className="tabular-nums text-[#ffe08a]">{c.count.toLocaleString()}</span>
                </span>
              ))}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
