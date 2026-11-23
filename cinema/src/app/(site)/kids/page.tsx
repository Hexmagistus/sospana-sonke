import type { Metadata } from "next";
import Link from "next/link";
import { MovieRow } from "@/components/movies";
import { isApprovedForKids, kidsByGroup, moviesInCategory, type KidsGroup } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "Kids Cinema",
  description: "Hand-reviewed films and cartoons for children. Nothing plays until a person has approved it.",
  alternates: { canonical: "/kids" },
};

const groups: Array<{ id: KidsGroup; label: string; copy: string }> = [
  { id: "preschool", label: "Preschool", copy: "Very short, no dialogue, nothing scary." },
  { id: "6-8", label: "Ages 6–8", copy: "Cartoons a reviewer cleared for this age." },
  { id: "9-12", label: "Ages 9–12", copy: "Longer films, still checked by a person." },
  { id: "family", label: "Family viewing", copy: "For a household watching together." },
];

export default async function KidsPage() {
  const catalog = await getPublicCatalog();
  const approved = catalog.movies.filter(isApprovedForKids);
  return (
    <main className="kids-world -mx-4 rounded-[2rem] px-4 py-8 sm:px-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-700">Kids Cinema</p>
      <h1 className="mt-2 font-display text-5xl text-stone-900">A quieter shelf</h1>
      <p className="mt-3 max-w-2xl text-stone-800">
        A person reviews every title before it is published here. Age labels are shown. Nothing starts playing on its own, and this shelf does not recommend films that failed that review.
      </p>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {groups.map((group) => (
          <Link key={group.id} href={`/kids/${group.id}`} className="rounded-3xl bg-white/80 p-4 shadow-sm">
            <span className="font-display text-2xl">{group.label}</span>
            <span className="mt-2 block text-sm text-stone-700">{group.copy}</span>
            <span className="mt-3 block text-sm font-semibold text-orange-700">{kidsByGroup(catalog.movies, group.id).length} titles</span>
          </Link>
        ))}
      </div>
      <MovieRow title="Approved for children" movies={approved} kids empty="Nothing has been approved yet." />
      <MovieRow title="Preschool" href="/kids/preschool" movies={kidsByGroup(catalog.movies, "preschool")} kids />
      <MovieRow title="Animated, approved" movies={moviesInCategory(catalog.movies, "kids-animated-movies")} kids />
      <MovieRow title="Science for kids" href="/categories/kids-science" movies={moviesInCategory(catalog.movies, "kids-science")} kids empty="No science title has been approved for children yet." />
      <MovieRow title="African children's stories" movies={moviesInCategory(catalog.movies, "kids-african-stories")} kids empty="No verified African children's story is in the catalogue yet." />
      <p className="mt-8 max-w-2xl text-sm text-stone-700">
        Animated films that were not approved, including Sintel, stay on the main animation shelf and are not linked from this page.
      </p>
    </main>
  );
}
