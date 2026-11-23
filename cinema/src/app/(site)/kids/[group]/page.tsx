import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MovieCard } from "@/components/movies";
import { KIDS_GROUPS, kidsByGroup, type KidsGroup } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";

const labels: Record<KidsGroup, string> = {
  preschool: "Preschool",
  "6-8": "Ages 6–8",
  "9-12": "Ages 9–12",
  family: "Family viewing",
};

export async function generateMetadata({ params }: { params: Promise<{ group: string }> }): Promise<Metadata> {
  const { group } = await params;
  if (!KIDS_GROUPS.includes(group as KidsGroup)) return { title: "Kids Cinema" };
  return { title: `${labels[group as KidsGroup]} · Kids Cinema`, alternates: { canonical: `/kids/${group}` } };
}

export default async function KidsGroupPage({ params }: { params: Promise<{ group: string }> }) {
  const { group } = await params;
  if (!KIDS_GROUPS.includes(group as KidsGroup)) notFound();
  const catalog = await getPublicCatalog();
  const movies = kidsByGroup(catalog.movies, group as KidsGroup);
  return (
    <main className="kids-world -mx-4 rounded-[2rem] px-4 py-8 sm:px-8">
      <Link href="/kids" className="text-sm font-semibold text-orange-700">
        Kids Cinema
      </Link>
      <h1 className="mt-2 font-display text-4xl text-stone-900">{labels[group as KidsGroup]}</h1>
      <p className="mt-3 max-w-2xl text-stone-800">Only titles a person marked for this age group are listed. Playback does not start by itself.</p>
      {movies.length === 0 ? <p className="mt-8 text-stone-700">Nothing in this age group has been approved.</p> : null}
      <div className="mt-6 flex flex-wrap gap-4">
        {movies.map((movie) => (
          <MovieCard key={movie.slug} movie={movie} kids />
        ))}
      </div>
    </main>
  );
}
