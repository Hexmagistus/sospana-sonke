import Link from "next/link";
import data from "@/data/opportunitiesToday.json";

type Post = { employer: string; closingDate: string | null; category?: string };

/** Short display name: the abbreviation in brackets if there is one, e.g. "Eskom" or "AGSA". */
function shortName(name: string) {
  const m = name.match(/\(([^)]+)\)\s*$/);
  return m ? m[1] : name;
}

/** Summary text generated from the opportunities data. */
function summary() {
  const today = new Date(Date.now() + 2 * 3600 * 1000).toISOString().slice(0, 10);
  const posts = (data as { posts: Post[] }).posts.filter((p) => !p.closingDate || p.closingDate >= today);
  if (posts.length === 0) return "See the latest posts checked on official careers pages. Free, no login.";
  const counts = new Map<string, number>();
  const cats: string[] = [];
  for (const p of posts) {
    counts.set(p.employer, (counts.get(p.employer) ?? 0) + 1);
    const raw = p.category ?? "other employers";
    const c = /^[A-Z][a-z]/.test(raw) ? raw[0].toLowerCase() + raw.slice(1) : raw;
    if (!cats.includes(c)) cats.push(c);
  }
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([e]) => shortName(e));
  const catText = cats.length > 1 ? `${cats.slice(0, -1).join(", ")} and ${cats[cats.length - 1]}` : cats[0];
  return `${posts.length} open posts at ${counts.size} employers, including ${top.join(", ")}. Covers ${catText}, checked on their official pages. Free, no login.`;
}

/** Prominent block linking to /opportunities-today (bright light card, gold top bar). */
export default function OpportunitiesTodayLink({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/opportunities-today"
      className={`block rounded-lg border border-[#1F2328]/10 border-l-[6px] border-l-[#1E7A47] bg-[#FFF8EC] p-4 text-[#1F2328] shadow-sm transition-colors hover:bg-[#FDF7E7] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#1F2328] motion-reduce:transition-none ${className}`}
    >
      <span className="block text-base font-bold tracking-tight sm:text-lg">🆕 Opportunities found today →</span>
      <span className="mt-1 block text-sm text-slate-700">{summary()}</span>
    </Link>
  );
}
