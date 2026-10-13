"use client";

import { useEffect, useId, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type Suggestions = { titles: string[]; employers: string[]; countries: string[] };

const empty: Suggestions = { titles: [], employers: [], countries: [] };

/** Keyword field that still submits with the form. Suggestions come from stored roles. */
export function RoleSuggestInput({ defaultValue, className }: { defaultValue: string; className: string }) {
  const listId = useId();
  const [value, setValue] = useState(defaultValue);
  const [suggestions, setSuggestions] = useState<Suggestions>(empty);

  useEffect(() => {
    const term = value.trim();
    if (term.length < 2) {
      setSuggestions(empty);
      return;
    }
    const timer = window.setTimeout(() => {
      fetch(`${API}/jobs/suggest?q=${encodeURIComponent(term)}`)
        .then((res) => (res.ok ? res.json() : empty))
        .then((data: Suggestions) => {
          setSuggestions({
            titles: Array.isArray(data.titles) ? data.titles.slice(0, 5) : [],
            employers: Array.isArray(data.employers) ? data.employers.slice(0, 5) : [],
            countries: Array.isArray(data.countries) ? data.countries.slice(0, 5) : [],
          });
        })
        .catch(() => setSuggestions(empty));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [value]);

  const options = [
    ...suggestions.titles,
    ...suggestions.employers,
    ...suggestions.countries,
  ];

  return (
    <>
      <input
        name="q"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Title, for example nurse or learnership"
        className={className}
        aria-autocomplete="list"
        aria-controls={options.length ? listId : undefined}
        autoComplete="off"
      />
      {options.length > 0 ? (
        <ul id={listId} role="listbox" className="mt-2 space-y-1 text-sm">
          {suggestions.titles.map((title) => (
            <li key={`t-${title}`} role="option">
              <button type="button" className="underline" onClick={() => setValue(title)}>
                {title}
              </button>
            </li>
          ))}
          {suggestions.employers.map((name) => (
            <li key={`e-${name}`} role="option">
              <a className="underline" href={`/jobs?employer=${encodeURIComponent(name)}`}>{name}</a>
            </li>
          ))}
          {suggestions.countries.map((name) => (
            <li key={`c-${name}`} role="option">
              <a className="underline" href={`/jobs?country=${encodeURIComponent(name)}`}>{name}</a>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}
