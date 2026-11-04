import Link from "next/link";
import data from "@/data/opportunitiesToday.json";

type Post = { employer: string; closingDate: string | null; sector?: string };

/** Short display name: the abbreviation in brackets if there is one, e.g. "Eskom" or "AGSA". */
function shortName(name: string) {
  const m = name.match(/\(([^)]+)\)\s*$/);
  return m ? m[1] : name;
}

/** Summary text generated from the opportunities data. */
function summary() {
  const today = new Date(Date.now() + 2 * 3600 * 1000).toISOString().slice(0, 10);
  const posts = (data as { posts: Post[] }).posts.filter((p) => !p.closingDate || p.closingDate >= today);
  const counts = new Map<string, number>();
  let uni = 0;
  for (const p of posts) {
    if (p.sector === "university") uni++;
    else counts.set(p.employer, (counts.get(p.employer) ?? 0) + 1);
  }
  if (posts.length === 0) return "See the latest posts checked on official careers pages. Free, no login.";
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([e]) => shortName(e));
  const shown = top.slice(0, 4);
  const more = top.length - shown.length;
  let text = `${posts.length} open posts at ${shown.join(", ")}`;
  if (more > 0) text += ` and ${more} more state-owned ${more === 1 ? "company" : "companies"}`;
  if (uni > 0) text += ", plus universities";
  return `${text}, checked on their official pages. Free, no login.`;
}

/** Prominent block linking to /opportunities-today (bright light card, gold top bar). */
export default function OpportunitiesTodayLink({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/opportunities-today"
      className={`block rounded-lg border border-[#07284C]/10 border-l-[6px] border-l-[#1E7A47] bg-[#FFF8EC] p-4 text-[#07284C] shadow-sm transition-colors hover:bg-[#FDF7E7] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#07284C] motion-reduce:transition-none ${className}`}
    >
      <span className="block text-base font-bold tracking-tight sm:text-lg">🆕 Opportunities found today →</span>
      <span className="mt-1 block text-sm text-slate-700">{summary()}</span>
    </Link>
  );
}
