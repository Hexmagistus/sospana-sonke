import type { Metadata } from "next";
import Link from "next/link";
import RecentPostsList from "@/components/RecentPostsList";
import { RECENT_PAGE_SIZE, RECENT_TYPES, fetchRecentPosts } from "@/lib/recentPosts";

export const revalidate = 900;

export const metadata: Metadata = {
  title: "Recently posted open jobs and internships | Sospana Sonke",
  description:
    "The newest open posts found on employers' official careers pages, newest first. Closed and expired posts are left out. Free, no login.",
};

const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575]";
const MAX_PAGES = 20; // the API allows offsets up to 1 000

type Search = Promise<{ type?: string; page?: string }>;

export default async function RecentPostsPage({ searchParams }: { searchParams: Search }) {
  const sp = await searchParams;
  const type = RECENT_TYPES.some((t) => t.id === sp.type) ? (sp.type as string) : "";
  const page = Math.min(Math.max(1, Number.parseInt(sp.page || "1", 10) || 1), MAX_PAGES);
  const data = await fetchRecentPosts({ limit: RECENT_PAGE_SIZE, offset: (page - 1) * RECENT_PAGE_SIZE, type });
  const posts = data?.posts ?? [];
  const matched = data?.matched ?? 0;
  const pages = Math.min(MAX_PAGES, Math.max(1, Math.ceil(matched / RECENT_PAGE_SIZE)));
  const href = (p: number, t = type) => {
    const q = new URLSearchParams();
    if (t) q.set("type", t);
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return s ? `/recent-posts?${s}` : "/recent-posts";
  };

  return (
    <div className="mx-auto max-w-5xl text-[#1F2328]">
      <div className="mb-6 rounded-2xl border border-[#1F2328]/10 border-t-4 border-t-[#E2AE3C] bg-white p-5 shadow-sm sm:p-6">
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">🆕 Recently posted</h1>
        <p className="mt-2 max-w-3xl text-base leading-relaxed text-[#3A3F47]">
          {data ? (
            <>
              <strong className="text-[#1F2328]">{matched.toLocaleString("en-ZA").replace(/,/g, " ")} open posts</strong>, newest
              first. &ldquo;Posted&rdquo; is the date on the advert; &ldquo;Added&rdquo; is when we first found it on the
              employer&apos;s careers page. Posts that are closed or past their closing date are left out.
            </>
          ) : (
            <>Our free server is waking up, so the list couldn&apos;t load just now. Please refresh in a minute.</>
          )}
        </p>
        <nav aria-label="Opportunity type" className="mt-4 flex flex-wrap gap-2">
          {RECENT_TYPES.map((t) => (
            <Link
              key={t.id || "all"}
              href={href(1, t.id)}
              aria-current={t.id === type ? "page" : undefined}
              className={`rounded-full border-2 px-4 py-1.5 text-sm font-bold ${FOCUS} ${
                t.id === type ? "border-[#0B2447] bg-[#0B2447] text-white" : "border-[#0B2447]/30 bg-white text-[#0B2447] hover:border-[#0B2447]"
              }`}
            >
              {t.label}
            </Link>
          ))}
        </nav>
      </div>

      {posts.length > 0 ? (
        <RecentPostsList posts={posts} />
      ) : (
        data && <p className="rounded-2xl bg-white px-4 py-4 text-[#3A3F47]">No open posts of this type right now. Try &ldquo;All&rdquo;.</p>
      )}

      {data && pages > 1 && (
        <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-3">
          {page > 1 ? (
            <Link href={href(page - 1)} className={`rounded-full border-2 border-[#0B2447] bg-white px-4 py-2 text-sm font-bold text-[#0B2447] ${FOCUS}`}>← Newer</Link>
          ) : <span />}
          <span className="text-sm text-[#4A4F57]">Page {page} of {pages}</span>
          {page < pages ? (
            <Link href={href(page + 1)} className={`rounded-full border-2 border-[#0B2447] bg-white px-4 py-2 text-sm font-bold text-[#0B2447] ${FOCUS}`}>Older →</Link>
          ) : <span />}
        </nav>
      )}
      <p className="mt-6 text-sm text-[#3A3F47]">
        Looking for a particular employer? See <Link href="/opportunities-today" className="font-semibold text-[#0B6575] underline">opportunities by employer</Link>.
        Apply only on the official links ✅
      </p>
    </div>
  );
}
