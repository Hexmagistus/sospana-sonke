import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { MovieEditor } from "@/components/admin-client";
import { movieBySlug } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";
import { currentAdmin } from "@/lib/session";

export const metadata: Metadata = { title: "Edit title", robots: { index: false } };

export default async function EditMoviePage({ params }: { params: Promise<{ slug: string }> }) {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  const movie = movieBySlug(catalog.movies, slug);
  if (!movie) notFound();
  return (
    <main>
      <h1 className="font-display text-4xl">Edit {movie.title}</h1>
      <p className="mt-2 text-sm text-ink/60">A new playback URL is stored only together with a licence evidence URL.</p>
      <div className="mt-6">
        <MovieEditor movie={movie} />
      </div>
    </main>
  );
}
