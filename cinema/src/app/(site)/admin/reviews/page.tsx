import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getPublicCatalog } from "@/lib/public-catalog";
import { currentAdmin } from "@/lib/session";

export const metadata: Metadata = { title: "Kids reviews", robots: { index: false } };

export default async function ReviewsPage() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const catalog = await getPublicCatalog();
  const reviewed = catalog.movies.filter((movie) => movie.review);
  return (
    <main>
      <h1 className="font-display text-4xl">Kids reviews</h1>
      <p className="mt-3 max-w-2xl text-sm text-ink/70">Approval is manual. A rejected animated film stays out of Kids Cinema.</p>
      <ul className="mt-6 space-y-3">
        {reviewed.map((movie) => (
          <li key={movie.slug} className="rounded-2xl border border-white/10 p-4 text-sm">
            <Link href={`/admin/movies/${movie.slug}`} className="font-semibold text-amber">{movie.title}</Link>
            <p className="mt-1 text-ink/70">{movie.review?.reviewStatus} · {movie.review?.ageSuitability}</p>
            <p className="mt-1">{movie.review?.reviewNotes}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
