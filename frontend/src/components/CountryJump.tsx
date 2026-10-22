"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { countrySlug, suggestCountries } from "@/lib/countryPage";

export type CountryJumpRow = { name: string; flag: string };

/** Public lookup. Each match opens that country's page. It does not search vacancies. */
export function CountryJump({ countries }: { countries: readonly CountryJumpRow[] }) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(-1);
  const matches = suggestCountries(query, countries, 6);
  const highlighted = active >= 0 && active < matches.length ? active : -1;

  return (
    <form
      className="rounded-2xl border border-ss-border bg-ss-surface p-4 shadow-sm sm:p-5"
      onSubmit={(event) => {
        event.preventDefault();
        const target = matches[highlighted] ?? matches[0];
        if (!target) return;
        window.location.assign(`/countries/${countrySlug(target.name)}`);
      }}
    >
      <label htmlFor={listId} className="block text-sm font-semibold text-ss-text">
        Look up a country
      </label>
      <p className="mt-1 text-sm text-ss-muted">
        Opens a public page for that country. The employer list is open to everyone, no account needed.
      </p>
      <input
        id={listId}
        role="combobox"
        aria-expanded={matches.length > 0}
        aria-controls={`${listId}-list`}
        aria-autocomplete="list"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(-1);
        }}
        onKeyDown={(event) => {
          if (!matches.length) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setActive((index) => (index + 1) % matches.length);
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((index) => (index <= 0 ? matches.length - 1 : index - 1));
          } else if (event.key === "Escape") {
            setActive(-1);
          }
        }}
        placeholder="South Africa, Kenya, Brazil…"
        className="mt-3 w-full rounded-xl border border-ss-border bg-ss-surface px-3.5 py-2.5 text-base text-ss-text placeholder:text-ss-muted focus:border-navy focus:outline-none"
      />
      {matches.length > 0 && (
        <ul id={`${listId}-list`} role="listbox" className="mt-2 overflow-hidden rounded-xl border border-ss-border">
          {matches.map((row, index) => (
            <li key={row.name} role="option" aria-selected={index === highlighted}>
              <Link
                href={`/countries/${countrySlug(row.name)}`}
                className={`flex items-center justify-between gap-3 px-3 py-2 text-sm ${
                  index === highlighted ? "bg-ss-primary-soft" : "hover:bg-ss-primary-soft"
                }`}
              >
                <span className="font-semibold text-ss-text">{row.flag} {row.name}</span>
                <span className="text-ss-muted">Public page</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
