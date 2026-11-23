import Link from "next/link";
import RecentPostsList from "@/components/RecentPostsList";
import { fetchRecentPosts } from "@/lib/recentPosts";

const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575]";

/** At most this many cards per employer, so one big same-day batch can't fill the section. */
const PER_EMPLOYER = 3;

/** Homepage "Recently posted": the newest open roles, refreshed every 15 minutes. */
export default async function RecentlyPosted({ limit = 18 }: { limit?: number }) {
  const data = await fetchRecentPosts({ limit: 50 });
  const seen = new Map<string, number>();
  const picked = (data?.posts ?? []).filter((p) => {
    const n = seen.get(p.company_name) ?? 0;
    seen.set(p.company_name, n + 1);
    return n < PER_EMPLOYER;
  });
  return (
    <section id="recently-posted" aria-labelledby="recent-h" className="scroll-mt-24 px-4 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="recent-h" className="border-l-4 border-[#E2AE3C] pl-3 text-2xl font-extrabold tracking-tight sm:text-3xl">
              🆕 Recently posted
            </h2>
            <p className="mt-2 max-w-2xl text-[#3A3F47]">
              The newest open posts we found on employers&apos; official careers pages, newest first (up to three per employer here). Closed and expired
              posts are left out. Apply only on the official link.
            </p>
          </div>
          <Link
            href="/recent-posts"
            className={`inline-flex items-center gap-2 rounded-full bg-[#0B2447] px-5 py-2.5 text-sm font-bold text-white shadow-md ring-2 ring-[#E2AE3C]/70 hover:bg-[#13315E] ${FOCUS}`}
          >
            See all recent →
          </Link>
        </div>
        {picked.length > 0 ? (
          <RecentPostsList posts={picked.slice(0, limit)} columns={3} />
        ) : (
          <p className="rounded-2xl border border-[#1F2328]/10 bg-white px-4 py-4 text-[#3A3F47]">
            The newest posts are loading from our free server, which can take a moment to wake up.{" "}
            <Link href="/recent-posts" className="font-semibold text-[#0B6575] underline">Open the recent posts list</Link> or see{" "}
            <Link href="/opportunities-today" className="font-semibold text-[#0B6575] underline">today&apos;s opportunities</Link>.
          </p>
        )}
      </div>
    </section>
  );
}
