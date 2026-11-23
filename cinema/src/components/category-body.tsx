import { moviesInCategory } from "@/lib/catalog";
import type { PublicCatalog } from "@/lib/public-catalog";
import { MovieCard } from "./movies";

export function CategoryBody({ catalog, slug }: { catalog: PublicCatalog; slug: string }) {
  const category = catalog.categories.find((item) => item.slug === slug);
  if (!category) return null;
  const movies = moviesInCategory(catalog.movies, slug).sort((a, b) => a.title.localeCompare(b.title));
  return (
    <main>
      <p className="text-xs uppercase tracking-[0.2em] text-amber">SOSPANA CINEMA</p>
      <h1 className="mt-2 font-display text-4xl">{category.name}</h1>
      <p className="mt-3 max-w-2xl text-ink/75">{category.description}</p>
      {movies.length === 0 ? (
        <p className="mt-8 rounded-2xl border border-dashed border-white/20 px-4 py-8 text-sm text-ink/70" data-testid="empty-category">
          {category.description}
        </p>
      ) : (
        <div className="mt-8 flex flex-wrap gap-4">
          {movies.map((movie) => (
            <MovieCard key={movie.slug} movie={movie} />
          ))}
        </div>
      )}
    </main>
  );
}
