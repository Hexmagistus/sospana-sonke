import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { LogoutButton } from "@/components/admin-client";
import { isApprovedForKids } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";
import { currentAdmin } from "@/lib/session";
import { adminTakedowns } from "@/lib/admin-takedowns";

export const metadata: Metadata = { title: "Admin", robots: { index: false, follow: false } };

export default async function AdminHome() {
  const admin = await currentAdmin();
  if (!admin) redirect("/admin/login");
  const catalog = await getPublicCatalog();
  const { items: takedowns } = await adminTakedowns();
  const withPlayback = catalog.movies.filter((movie) => movie.sources.some((source) => source.rightsVerified && source.playbackStatus === "available"));
  const approved = catalog.movies.filter(isApprovedForKids);
  const rejected = catalog.movies.filter((movie) => movie.review?.reviewStatus === "rejected");
  return (
    <main data-testid="admin-dashboard">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-display text-4xl">Catalogue desk</h1>
        <LogoutButton />
      </div>
      <p className="mt-2 text-sm text-ink/60">Signed in as {admin.email}. Source: {catalog.origin}.</p>
      {catalog.warning ? <p className="mt-2 text-sm text-coral">{catalog.warning}</p> : null}
      <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Titles" value={catalog.movies.length} />
        <Stat label="With a player" value={withPlayback.length} />
        <Stat label="Kids approved" value={approved.length} />
        <Stat label="Kids rejected" value={rejected.length} />
        <Stat label="Complaints" value={takedowns.length} />
        <Stat label="Sources" value={catalog.sources.length} />
      </dl>
      <nav className="mt-8 flex flex-wrap gap-3 text-sm">
        <Link className="rounded-full border border-white/15 px-3 py-2" href="/admin/movies">Titles</Link>
        <Link className="rounded-full border border-white/15 px-3 py-2" href="/admin/reviews">Kids reviews</Link>
        <Link className="rounded-full border border-white/15 px-3 py-2" href="/admin/takedowns">Complaints</Link>
        <Link className="rounded-full border border-white/15 px-3 py-2" href="/admin/sources">Sources</Link>
        <Link className="rounded-full border border-white/15 px-3 py-2" href="/admin/discovery">Discovery</Link>
      </nav>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <dt className="text-xs text-ink/50">{label}</dt>
      <dd className="font-display text-3xl">{value}</dd>
    </div>
  );
}
