import type { Metadata } from "next";
import { LibraryClient } from "@/components/library-client";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "On this device",
  robots: { index: false, follow: false },
};

export default async function LibraryPage() {
  const catalog = await getPublicCatalog();
  return (
    <main>
      <h1 className="font-display text-4xl">On this device</h1>
      <p className="mt-3 max-w-2xl text-ink/75">Favourites and resume points stay in this browser. Sospana Cinema does not ask for an email or a phone number.</p>
      <div className="mt-8">
        <LibraryClient movies={catalog.movies} />
      </div>
    </main>
  );
}
