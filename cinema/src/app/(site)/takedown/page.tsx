import type { Metadata } from "next";
import { TakedownForm } from "@/components/takedown-form";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "Copyright complaint",
  description: "Ask Sospana Cinema to review a title you believe should not be listed.",
  alternates: { canonical: "/takedown" },
};

export default async function TakedownPage() {
  const catalog = await getPublicCatalog();
  return (
    <main>
      <h1 className="font-display text-4xl">Copyright complaint</h1>
      <p className="mt-3 max-w-2xl text-ink/75">
        If you are the rights holder, or you represent them, tell us which title and why it should come down. We keep your name and email only to answer the complaint. There is no viewer account.
      </p>
      <div className="mt-6">
        <TakedownForm movies={catalog.movies.filter((movie) => movie.published)} />
      </div>
    </main>
  );
}
