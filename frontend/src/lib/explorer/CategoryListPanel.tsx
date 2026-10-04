"use client";

import { splitColumns, type CategoryListItem } from "./categoryList";
import { NOT_COUNTED_LABEL } from "../notCounted";

type Props = {
  items: readonly CategoryListItem[];
  /** "Private" / "All categories". */
  category: string;
  /** Country name, or "" for all countries. */
  country: string;
  noun?: string;
};

function Entry({ item }: { item: CategoryListItem }) {
  const bracket = item.counted ? (
    <span className="tabular-nums text-ss-primary">({item.value})</span>
  ) : (
    <span className="text-ss-muted">
      (<abbr title={`NCY = ${NOT_COUNTED_LABEL}. We cannot read their vacancies yet. This is not “no jobs”: check their careers page.`} className="cursor-help no-underline decoration-dotted underline-offset-2 hover:underline">NCY</abbr>)
    </span>
  );
  return (
    <li className="min-w-0 break-words py-0.5 text-[13px] leading-snug">
      {item.url ? (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          title={`Open ${item.name}'s careers page`}
          className="font-semibold text-ss-text underline-offset-2 hover:text-ss-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold"
        >
          {item.name}
        </a>
      ) : (
        <span className="font-semibold text-ss-text" title="No careers page yet">{item.name}</span>
      )}{" "}
      {bracket}
    </li>
  );
}

/**
 * Names of every company in the chosen country and category, with the vacancy count in
 * brackets. From md up it sits over the map as two translucent scrollable columns; on small
 * screens it is one scrollable box under the map. One set of links in the page either way.
 */
export function CategoryListPanel({ items, category, country, noun = "companies" }: Props) {
  if (items.length === 0) return null;
  const [left, right] = splitColumns(items);
  const colClass =
    "md:max-h-full md:w-[27%] md:min-w-[11rem] md:self-start md:overflow-y-auto md:rounded-xl md:border md:border-ss-border md:bg-ss-panel md:p-3 md:shadow-lg md:backdrop-blur-sm md:pointer-events-auto";
  return (
    <section
      aria-label={`${category} ${noun} in ${country || "all countries"}`}
      data-testid="category-list"
      className="mt-2 max-h-72 overflow-y-auto rounded-xl border border-ss-border bg-ss-panel p-3 text-ss-text md:pointer-events-none md:absolute md:inset-0 md:mt-0 md:flex md:max-h-none md:justify-between md:gap-3 md:overflow-visible md:rounded-none md:border-0 md:bg-transparent md:p-3"
    >
      <div className={colClass}>
        <h3 className="text-xs font-extrabold uppercase tracking-wider text-ss-primary">
          {category} · <span data-testid="category-list-count">{items.length}</span> {items.length === 1 ? noun.replace(/ies$/, "y").replace(/s$/, "") : noun}
        </h3>
        <p className="mb-1.5 mt-0.5 text-[11px] leading-snug text-ss-muted">
          (number) = vacancies counted. <abbr title="Not counted yet" className="no-underline">NCY</abbr> = {NOT_COUNTED_LABEL}, not “no jobs”.
        </p>
        <ul className="space-y-0">{left.map((i) => <Entry key={i.id} item={i} />)}</ul>
      </div>
      {right.length > 0 && (
        <div className={colClass}>
          <ul className="space-y-0">{right.map((i) => <Entry key={i.id} item={i} />)}</ul>
        </div>
      )}
    </section>
  );
}
