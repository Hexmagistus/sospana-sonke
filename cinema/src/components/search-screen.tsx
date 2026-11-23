"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { countryOptions } from "@/lib/countries";
import { browserLibrary } from "@/lib/local-library";
import { searchMovies, type SearchQuery } from "@/lib/search";
import type { Category, Movie } from "@/lib/types";
import { useI18n } from "./i18n-provider";
import { MovieCard } from "./movies";

export function SearchScreen({
  movies,
  categories,
  initial,
}: {
  movies: Movie[];
  categories: Category[];
  initial: SearchQuery;
}) {
  const { t } = useI18n();
  const router = useRouter();
  const [draft, setDraft] = useState(initial.q ?? "");
  const query = { ...initial, q: draft };
  const result = searchMovies(movies, query);
  const countries = countryOptions(movies.map((movie) => movie.country));
  const languages = Array.from(new Set(movies.map((movie) => movie.language))).sort();
  const genres = Array.from(new Set(movies.flatMap((movie) => movie.genres))).sort();
  const [history, setHistory] = useState<string[]>([]);
  useEffect(() => setHistory(browserLibrary().read().searches), []);

  function push(next: SearchQuery) {
    const params = new URLSearchParams();
    if (next.q) params.set("q", next.q);
    if (next.country) params.set("country", next.country);
    if (next.language) params.set("language", next.language);
    if (next.genre) params.set("genre", next.genre);
    if (next.category) params.set("category", next.category);
    if (next.yearFrom) params.set("from", String(next.yearFrom));
    if (next.yearTo) params.set("to", String(next.yearTo));
    if (next.sort && next.sort !== "relevance") params.set("sort", next.sort);
    if (next.kidsOnly) params.set("kids", "1");
    router.push(params.size ? `/search?${params}` : "/search");
  }

  return (
    <div>
      <form
        className="grid gap-3"
        action="/search"
        onSubmit={() => {
          if (draft.trim()) browserLibrary().rememberSearch(draft.trim());
        }}
      >
        <label className="block">
          <span className="sr-only">Search</span>
          <input
            name="q"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t("search.placeholder")}
            className="w-full rounded-2xl border border-white/15 bg-black/30 px-4 py-3 text-lg"
            autoComplete="off"
            data-testid="search-input"
          />
        </label>
        {draft.trim().length > 1 ? (
          <ul className="flex flex-wrap gap-2" aria-label="Suggestions">
            {searchMovies(movies, { q: draft }).hits.slice(0, 5).map((hit) => (
              <li key={hit.movie.slug}>
                <Link href={`/movies/${hit.movie.slug}`} className="rounded-full bg-white/10 px-3 py-1 text-sm">
                  {hit.movie.title}
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
          <Select name="country" label="Country" value={initial.country ?? ""} options={countries} onChange={(country) => push({ ...query, country })} />
          <Select name="language" label="Language" value={initial.language ?? ""} options={languages} onChange={(language) => push({ ...query, language })} />
          <Select name="genre" label="Genre" value={initial.genre ?? ""} options={genres} onChange={(genre) => push({ ...query, genre })} />
          <Select
            name="category"
            label="Category"
            value={initial.category ?? ""}
            options={categories.map((category) => category.slug)}
            labels={Object.fromEntries(categories.map((category) => [category.slug, category.name]))}
            onChange={(category) => push({ ...query, category })}
          />
          <label className="text-xs text-ink/70">
            From year
            <input name="from" defaultValue={initial.yearFrom ?? ""} inputMode="numeric" className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-2 py-2 text-sm text-ink" />
          </label>
          <label className="text-xs text-ink/70">
            To year
            <input name="to" defaultValue={initial.yearTo ?? ""} inputMode="numeric" className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-2 py-2 text-sm text-ink" />
          </label>
          <label className="text-xs text-ink/70">
            Sort
            <select name="sort" defaultValue={initial.sort ?? "relevance"} className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-2 py-2 text-sm text-ink">
              <option value="relevance">Relevance</option>
              <option value="newest">Recently added</option>
              <option value="title">Title</option>
              <option value="year">Year</option>
              <option value="runtime">Runtime</option>
            </select>
          </label>
          <label className="flex items-center gap-2 self-end text-sm">
            <input type="checkbox" name="kids" value="1" defaultChecked={initial.kidsOnly} />
            Kids approved only
          </label>
        </div>
        <button type="submit" className="w-fit rounded-full bg-amber px-4 py-2 text-sm font-semibold text-stone-950">
          Search
        </button>
      </form>
      {history.length > 0 ? (
        <p className="mt-4 text-sm text-ink/60">
          Recent searches on this device: {history.join(", ")}
        </p>
      ) : null}
      {result.corrected ? (
        <p className="mt-4 text-sm text-amber" data-testid="search-correction">
          No exact title match. Closest title: {result.corrected}.
        </p>
      ) : null}
      <p className="mt-4 text-sm text-ink/70" data-testid="search-count">
        {result.hits.length} title{result.hits.length === 1 ? "" : "s"}
      </p>
      <div className="mt-4 flex flex-wrap gap-4">
        {result.hits.map((hit) => (
          <MovieCard key={hit.movie.slug} movie={hit.movie} />
        ))}
      </div>
      {result.hits.length === 0 ? <p className="mt-6 text-ink/70">Nothing in the verified catalogue matches those filters.</p> : null}
    </div>
  );
}

function Select({
  name,
  label,
  value,
  options,
  labels,
  onChange,
}: {
  name: string;
  label: string;
  value: string;
  options: string[];
  labels?: Record<string, string>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs text-ink/70">
      {label}
      <select
        name={name}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-xl border border-white/15 bg-black/30 px-2 py-2 text-sm text-ink"
      >
        <option value="">Any</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {labels?.[option] ?? option}
          </option>
        ))}
      </select>
    </label>
  );
}
