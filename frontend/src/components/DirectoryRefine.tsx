"use client";

import { useId, useState } from "react";
import { Input } from "@/components/ui";
import type { BoardFilter, ScopeFilter } from "@/lib/directoryQuery";

const BOARDS: { id: BoardFilter; label: string }[] = [
  { id: "all", label: "All in this list" },
  { id: "open", label: "Open roles we counted" },
  { id: "linked", label: "Has a careers link" },
  { id: "blank", label: "No careers link yet" },
];

const SCOPES: { id: ScopeFilter; label: string }[] = [
  { id: "all", label: "Any link" },
  { id: "country", label: "Country filter" },
  { id: "unfiltered", label: "No country filter" },
  { id: "own", label: "Employer's page" },
  { id: "board", label: "Third-party board" },
];

function Chip({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition ${
        pressed
          ? "border-navy bg-navy text-white"
          : "border-ss-border bg-ss-surface text-ss-text hover:border-navy"
      }`}
    >
      {children}
    </button>
  );
}

/** Name search plus the two filters the loaded rows can answer honestly. */
export function DirectoryRefine({
  query,
  onQuery,
  suggestions,
  board,
  onBoard,
  scope,
  onScope,
  resultCount,
}: {
  query: string;
  onQuery: (value: string) => void;
  suggestions: readonly string[];
  board: BoardFilter;
  onBoard: (value: BoardFilter) => void;
  scope: ScopeFilter;
  onScope: (value: ScopeFilter) => void;
  resultCount: number;
}) {
  const listId = useId();
  const [active, setActive] = useState(-1);
  const shown = query.trim() ? suggestions : [];
  const highlighted = active >= 0 && active < shown.length ? active : -1;

  function pick(name: string) {
    onQuery(name);
    setActive(-1);
  }

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor={`${listId}-q`} className="mb-1 block text-sm font-semibold text-ss-text">
          Search employers in this list
        </label>
        <Input
          id={`${listId}-q`}
          role="combobox"
          aria-expanded={shown.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={highlighted >= 0 ? `${listId}-${highlighted}` : undefined}
          placeholder="Name or listing code"
          value={query}
          onChange={(e) => {
            onQuery(e.target.value);
            setActive(-1);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown" && shown.length) {
              e.preventDefault();
              setActive((i) => (i + 1) % shown.length);
            } else if (e.key === "ArrowUp" && shown.length) {
              e.preventDefault();
              setActive((i) => (i <= 0 ? shown.length - 1 : i - 1));
            } else if (e.key === "Enter" && highlighted >= 0) {
              e.preventDefault();
              pick(shown[highlighted]);
            } else if (e.key === "Escape") {
              setActive(-1);
            }
          }}
        />
        {shown.length > 0 && (
          <ul id={listId} role="listbox" className="mt-1 overflow-hidden rounded-xl border border-ss-border bg-ss-surface">
            {shown.map((name, index) => (
              <li key={name} id={`${listId}-${index}`} role="option" aria-selected={index === highlighted}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pick(name)}
                  className={`block w-full px-3 py-2 text-left text-sm ${
                    index === highlighted ? "bg-ss-primary-soft text-ss-text" : "text-ss-text hover:bg-ss-primary-soft"
                  }`}
                >
                  {name}
                </button>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-1.5 text-sm text-ss-muted">
          {resultCount === 1 ? "1 employer matches." : `${resultCount} employers match.`}
          {" "}Filters apply to the employers already loaded for this country or category.
        </p>
      </div>
      <fieldset className="min-w-0">
        <legend className="mb-1 text-sm font-semibold text-ss-text">Careers link</legend>
        <div className="flex flex-wrap gap-2">
          {BOARDS.map((item) => (
            <Chip key={item.id} pressed={board === item.id} onClick={() => onBoard(item.id)}>{item.label}</Chip>
          ))}
        </div>
      </fieldset>
      <fieldset className="min-w-0">
        <legend className="mb-1 text-sm font-semibold text-ss-text">Where the link points</legend>
        <div className="flex flex-wrap gap-2">
          {SCOPES.map((item) => (
            <Chip key={item.id} pressed={scope === item.id} onClick={() => onScope(item.id)}>{item.label}</Chip>
          ))}
        </div>
      </fieldset>
    </div>
  );
}

/** Placeholder cards while a country slice is still loading. */
export function DirectoryCardSkeleton({ label }: { label: string }) {
  return (
    <div className="md:col-span-2 space-y-3" aria-busy="true" aria-live="polite">
      <p className="text-sm text-ss-muted">{label}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {[0, 1].map((key) => (
          <div key={key} className="h-40 animate-pulse rounded-2xl border border-ss-border bg-ss-surface" />
        ))}
      </div>
    </div>
  );
}
