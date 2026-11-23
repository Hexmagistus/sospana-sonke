import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getPublicCatalog } from "@/lib/public-catalog";
import { currentAdmin } from "@/lib/session";

export const metadata: Metadata = { title: "Admin titles", robots: { index: false } };

export default async function AdminMoviesPage() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const catalog = await getPublicCatalog();
  return (
    <main>
      <h1 className="font-display text-4xl">Titles</h1>
      <ul className="mt-6 divide-y divide-white/10">
        {catalog.movies.map((movie) => (
          <li key={movie.slug} className="flex items-center justify-between gap-3 py-3 text-sm">
            <span>
              {movie.title} <span className="text-ink/50">{movie.releaseYear}</span>
            </span>
            <Link href={`/admin/movies/${movie.slug}`} className="text-amber">
              Edit
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
