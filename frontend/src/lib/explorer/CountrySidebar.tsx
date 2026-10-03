"use client";

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  GROUPS, fold, groupOf, groupRows, listedCountryCount, navigableRows,
  type CountryRow, type GroupId,
} from "../countryExplorer";

type Props = {
  rows: readonly CountryRow[];
  /** Selected country name. "" means All countries. */
  selected: string;
  onSelect: (name: string) => void;
  /** Noun for the sub-text, e.g. "employers", "universities". */
  noun?: string;
  /** Whether "All countries" can be picked in the current view. */
  allowAll?: boolean;
  /** Groups open on first render. Default: none (tests pass some). */
  initialExpanded?: readonly GroupId[];
};

/** Left side of the split view: search and the grouped country list. Navy panel in both themes. */
export function CountrySidebar({
  rows, selected, onSelect, noun = "employers", allowAll = true, initialExpanded,
}: Props) {
  const uid = useId();
  const searchRef = useRef<HTMLInputElement | null>(null);
  const optionRefs = useRef(new Map<string, HTMLLIElement>());
  const listRef = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState("");
  // Every group starts folded, the one holding the selected country included. A group opens
  // only when its header is clicked, or while a search is showing its matches.
  const selectedGroup = selected && rows.some((r) => r.name === selected) ? groupOf(selected) : null;
  const [expanded, setExpanded] = useState<Set<GroupId>>(() => new Set(initialExpanded ?? []));
  const collapsed = useMemo(() => new Set(GROUPS.map((g) => g.id).filter((id) => !expanded.has(id))), [expanded]);
  const [focusName, setFocusName] = useState<string | null>(null);

  const searching = fold(query) !== "";
  const groups = useMemo(() => groupRows(rows, query), [rows, query]);
  const navigable = useMemo(() => navigableRows(groups, collapsed, searching), [groups, collapsed, searching]);
  const total = listedCountryCount(rows);

  // "/" jumps to the search box, like a command bar. Ctrl+F is left to the browser.
  useEffect(() => {
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      e.preventDefault();
      searchRef.current?.focus();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // One tab stop for the whole list: the focused option, else the selected one, else the first.
  const tabStop = (focusName && navigable.some((r) => r.name === focusName) ? focusName : null)
    ?? (navigable.some((r) => r.name === selected) ? selected : null)
    ?? navigable[0]?.name ?? null;

  function moveFocus(e: KeyboardEvent<HTMLElement>, current: string) {
    const idx = navigable.findIndex((r) => r.name === current);
    let next = idx;
    if (e.key === "ArrowDown") next = Math.min(navigable.length - 1, idx + 1);
    else if (e.key === "ArrowUp") next = Math.max(0, idx - 1);
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = navigable.length - 1;
    else return;
    e.preventDefault();
    const target = navigable[next];
    if (!target) return;
    setFocusName(target.name);
    optionRefs.current.get(target.name)?.focus();
  }

  function toggle(id: GroupId) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // Keep the selected country in view inside the list (South Africa on first open).
  // Scrolls the list itself, never the page.
  useEffect(() => {
    const box = listRef.current;
    const el = selected ? optionRefs.current.get(selected) : null;
    if (!box || !el) return;
    const top = el.offsetTop; // the list is the offsetParent (position: relative)
    if (top < box.scrollTop || top + el.offsetHeight > box.scrollTop + box.clientHeight) {
      box.scrollTop = Math.max(0, top - 48);
    }
  }, [selected, rows, expanded]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 text-white">
      <div className="relative">
        <label htmlFor={`${uid}-search`} className="sr-only">Search countries</label>
        <input
          id={`${uid}-search`}
          ref={searchRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Browse from…"
          autoComplete="off"
          className="w-full rounded-lg border border-white/15 bg-black/30 py-2 pl-3 pr-10 text-sm text-white placeholder:text-blue-300/80 focus:border-gold"
        />
        <kbd aria-hidden className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-white/20 px-1.5 py-0.5 text-[10px] font-semibold text-blue-200">/</kbd>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
          <div className="mb-1 flex items-center justify-between px-1">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-blue-200">Countries ({total})</h3>
            {allowAll && (
              <button
                type="button"
                onClick={() => onSelect("")}
                aria-pressed={selected === ""}
                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${selected === "" ? "bg-gold text-navy" : "text-[#ffe08a] hover:bg-white/10"}`}
              >
                All countries
              </button>
            )}
          </div>
          <div ref={listRef} className="relative max-h-[22rem] min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 lg:max-h-none" data-testid="country-list">
            {groups.length === 0 && (
              <p className="px-2 py-4 text-sm text-blue-200">No country matches “{query.trim()}”.</p>
            )}
            {groups.map((g) => {
              const open = searching || !collapsed.has(g.id);
              const listId = `${uid}-group-${g.id}`;
              return (
                <section key={g.id} aria-label={g.label}>
                  <h4 className="m-0">
                    <button
                      type="button"
                      aria-expanded={open}
                      aria-controls={listId}
                      onClick={() => toggle(g.id)}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[11px] font-bold uppercase tracking-wider text-blue-200 hover:bg-white/5"
                    >
                      <span aria-hidden className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
                      <span className="flex-1">
                        {g.label}
                        {!open && selectedGroup === g.id && (
                          <>
                            <span aria-hidden title={`${selected} is selected`} className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-gold align-middle" />
                            <span className="sr-only"> (contains the selected country, {selected})</span>
                          </>
                        )}
                      </span>
                      <span className="rounded-full bg-white/10 px-1.5 text-[10px] tabular-nums">{g.rows.length}</span>
                    </button>
                  </h4>
                  {open && (
                    <ul id={listId} role="listbox" aria-label={`${g.label} countries`} className="mt-0.5 space-y-0.5">
                      {g.rows.map((r) => {
                        const isSelected = selected === r.name;
                        return (
                          <li
                            key={r.name}
                            ref={(el) => {
                              if (el) optionRefs.current.set(r.name, el);
                              else optionRefs.current.delete(r.name);
                            }}
                            role="option"
                            aria-selected={isSelected}
                            aria-disabled={r.selectable ? undefined : true}
                            tabIndex={r.selectable && tabStop === r.name ? 0 : -1}
                            data-country={r.code ?? r.name}
                            onFocus={() => r.selectable && setFocusName(r.name)}
                            onClick={() => r.selectable && onSelect(r.name)}
                            onKeyDown={(e) => {
                              if (!r.selectable) return;
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                onSelect(r.name);
                              } else moveFocus(e, r.name);
                            }}
                            className={`relative flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm outline-none transition-colors ${
                              r.selectable ? "cursor-pointer hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-gold" : "cursor-not-allowed opacity-45"
                            } ${isSelected ? "bg-white/10" : ""}`}
                          >
                            {isSelected && <span aria-hidden className="absolute inset-y-1.5 left-0 w-1 rounded-full bg-gold" />}
                            <span aria-hidden className="w-6 shrink-0 text-center text-xl leading-none">{r.flag}</span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-semibold text-white">{r.name}</span>
                              <span className="block text-[11px] text-blue-200">
                                {r.selectable ? `${r.employers.toLocaleString()} ${r.employers === 1 && noun === "employers" ? "employer" : noun}` : "No employers yet"}
                              </span>
                            </span>
                            {r.selectable && r.counted > 0 && (
                              <span
                                title={`${r.counted} of ${r.employers} have a counted vacancy result. The rest say “Not counted yet”.`}
                                className="shrink-0 rounded-full border border-gold/60 bg-gold/15 px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-[#ffe08a]"
                              >
                                {r.counted} counted
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </section>
              );
            })}
          </div>
        </div>
    </div>
  );
}
