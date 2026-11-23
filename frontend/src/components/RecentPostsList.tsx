import { fmtDay, placeOf, postedLabel, todaySA, typeTag, type RecentPost } from "@/lib/recentPosts";

const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B6575]";

/** Cards for recently posted open roles (server component, no client JS). */
export default function RecentPostsList({ posts, columns = 2 }: { posts: RecentPost[]; columns?: 2 | 3 }) {
  const today = todaySA();
  return (
    <ul className={`grid gap-3 sm:grid-cols-2 ${columns === 3 ? "lg:grid-cols-3" : ""}`}>
      {posts.map((p) => {
        const tag = typeTag(p.opportunity_type);
        const place = placeOf(p);
        const href = p.application_url || undefined;
        const body = (
          <>
            <span className="flex items-start justify-between gap-2">
              <span className="min-w-0 font-bold leading-snug text-[#1F2328]">{p.title}</span>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold ${tag.cls}`}>{tag.label}</span>
            </span>
            <span className="mt-1 block text-sm font-semibold text-[#0B2447]">{p.company_name}</span>
            {place && <span className="block text-sm text-[#3A3F47]">📍 {place}</span>}
            <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
              <span className="font-semibold text-[#1E6B40]">🕒 {postedLabel(p, today)}</span>
              <span className="font-medium text-[#9A3722]">
                {p.closing_date ? `Closes ${fmtDay(p.closing_date)}` : "No closing date shown"}
              </span>
            </span>
            {href && <span className="mt-2 inline-block text-sm font-bold text-[#0B6575] underline">Apply on the official site →</span>}
          </>
        );
        return (
          <li key={p.id}>
            {href ? (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={`block h-full rounded-2xl border border-[#1F2328]/12 border-l-4 border-l-[#E2AE3C] bg-white px-4 py-3 shadow-sm transition hover:-translate-y-0.5 hover:border-l-[#B8432A] hover:shadow-md motion-reduce:transition-none ${FOCUS}`}
              >
                {body}
              </a>
            ) : (
              <div className="block h-full rounded-2xl border border-[#1F2328]/12 border-l-4 border-l-[#E2AE3C] bg-white px-4 py-3 shadow-sm">{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
