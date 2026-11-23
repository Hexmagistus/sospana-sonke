"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { browserLibrary, type LibraryState } from "@/lib/local-library";
import type { Movie } from "@/lib/types";
import { useI18n } from "./i18n-provider";

export function LibraryClient({ movies }: { movies: Movie[] }) {
  const { t } = useI18n();
  const [state, setState] = useState<LibraryState | null>(null);
  useEffect(() => setState(browserLibrary().read()), []);
  if (!state) return <p className="text-sm text-ink/60">Reading what is saved on this device…</p>;
  const bySlug = new Map(movies.map((movie) => [movie.slug, movie]));
  return (
    <div>
      <section>
        <h2 className="font-display text-2xl">{t("library.favourites")}</h2>
        {state.favourites.length === 0 ? <p className="mt-2 text-sm text-ink/70">No favourites saved on this device.</p> : null}
        <ul className="mt-3 space-y-2">
          {state.favourites.map((slug) => (
            <li key={slug}>
              <Link href={`/movies/${slug}`} className="text-amber">
                {bySlug.get(slug)?.title ?? slug}
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <section className="mt-8" data-testid="library-continue">
        <h2 className="font-display text-2xl">{t("library.continue")}</h2>
        {state.progress.length === 0 ? <p className="mt-2 text-sm text-ink/70">Nothing to resume yet.</p> : null}
        <ul className="mt-3 space-y-2">
          {state.progress.map((item) => (
            <li key={item.slug}>
              <Link href={`/watch/${item.slug}`} className="text-amber">
                {item.title}
              </Link>
              <span className="ml-2 text-sm text-ink/60">
                {item.player === "embed" ? "archive player restarts" : `${Math.floor(item.position)} seconds`}
              </span>
            </li>
          ))}
        </ul>
      </section>
      <section className="mt-8" id="clear">
        <h2 className="font-display text-2xl">{t("cta.clear")}</h2>
        <p className="mt-2 max-w-xl text-sm text-ink/70">
          Favourites, continue watching, search history, language and the country you picked are stored in this browser only. Nothing is sent to an account, because there is no viewer account.
        </p>
        <button
          type="button"
          data-testid="clear-local"
          className="mt-4 rounded-full bg-coral px-4 py-2 text-sm font-semibold text-white"
          onClick={() => {
            browserLibrary().clear();
            window.localStorage.removeItem("sospana-cinema-locale");
            setState(browserLibrary().read());
          }}
        >
          {t("cta.clear")}
        </button>
      </section>
    </div>
  );
}
