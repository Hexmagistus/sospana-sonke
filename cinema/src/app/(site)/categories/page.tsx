import type { Metadata } from "next";
import Link from "next/link";
import { moviesInCategory } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "Categories",
  description: "Browse Sospana Cinema by category.",
  alternates: { canonical: "/categories" },
};

export default async function CategoriesPage() {
  const catalog = await getPublicCatalog();
  return (
    <main>
      <h1 className="font-display text-4xl">Categories</h1>
      <p className="mt-3 max-w-2xl text-ink/75">Each shelf only lists titles whose licence was checked. Empty shelves stay empty.</p>
      <ul className="mt-8 grid gap-3 sm:grid-cols-2">
        {catalog.categories.map((category) => {
          const count = moviesInCategory(catalog.movies, category.slug).length;
          return (
            <li key={category.slug}>
              <Link href={`/categories/${category.slug}`} className="block rounded-2xl border border-white/10 bg-white/5 px-4 py-4 hover:border-amber/50">
                <span className="font-display text-xl">{category.name}</span>
                <span className="mt-1 block text-sm text-ink/60">{count} verified {count === 1 ? "title" : "titles"}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
