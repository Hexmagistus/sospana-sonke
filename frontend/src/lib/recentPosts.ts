/**
 * "Recently posted" open roles, read server-side from the public API
 * (GET /jobs?sort=recent). Open means: not closed, not expired, and the closing
 * date (when stated) is today or later — the API applies those rules.
 *
 * Pages that use this are statically rendered and refreshed every 15 minutes
 * (ISR). If the API is asleep or down, callers get `null` and show a fallback,
 * so the page itself never fails.
 */
export const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || "https://sospana-sonke-api-fra.onrender.com/api/v1";
export const RECENT_REVALIDATE = 900;
export const RECENT_PAGE_SIZE = 50; // the API's per-request cap

export type RecentPost = {
  id: string;
  title: string;
  company_name: string;
  company_country: string | null;
  location: string | null;
  country: string | null;
  posting_date: string | null;
  closing_date: string | null;
  first_seen_at: string | null;
  application_url: string | null;
  opportunity_type: string;
};

export const RECENT_TYPES = [
  { id: "", label: "All" },
  { id: "job", label: "Jobs" },
  { id: "internship", label: "Internships" },
  { id: "learnership", label: "Learnerships" },
  { id: "graduate_programme", label: "Graduate programmes" },
  { id: "bursary", label: "Bursaries" },
] as const;

export async function fetchRecentPosts(
  { limit = 20, offset = 0, type = "" }: { limit?: number; offset?: number; type?: string } = {},
): Promise<{ posts: RecentPost[]; matched: number } | null> {
  const params = new URLSearchParams({ sort: "recent", limit: String(Math.min(limit, RECENT_PAGE_SIZE)), offset: String(offset) });
  if (type) params.set("opportunity_type", type);
  try {
    const res = await fetch(`${API_ORIGIN}/jobs?${params}`, {
      next: { revalidate: RECENT_REVALIDATE },
      signal: AbortSignal.timeout(12000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { jobs?: RecentPost[]; matched?: number };
    const today = todaySA();
    const posts = (data.jobs ?? []).filter((p) => !p.closing_date || p.closing_date >= today);
    return { posts, matched: data.matched ?? posts.length };
  } catch {
    return null;
  }
}

/** Today's date in South Africa (UTC+2, no DST) as YYYY-MM-DD. */
export function todaySA(now = Date.now()): string {
  return new Date(now + 2 * 3600 * 1000).toISOString().slice(0, 10);
}

/** The South African calendar day of an ISO date or timestamp. */
export function saDay(iso: string): string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? iso.slice(0, 10) : todaySA(t);
}

const daysBetween = (a: string, b: string) => Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86400000);

function ago(days: number): string {
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 14) return "1 week ago";
  if (days < 60) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

/** "Posted 2 days ago" from the advert's own date, else "Added …" (first found by our scanner). */
export function postedLabel(p: Pick<RecentPost, "posting_date" | "first_seen_at">, today = todaySA()): string {
  if (p.posting_date) return `Posted ${ago(daysBetween(p.posting_date, today))}`;
  if (p.first_seen_at) return `Added ${ago(daysBetween(saDay(p.first_seen_at), today))}`;
  return "Recently added";
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function fmtDay(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

export function placeOf(p: Pick<RecentPost, "location" | "country" | "company_country">): string {
  const country = p.country || p.company_country || "";
  const loc = (p.location || "").trim();
  if (!loc) return country;
  if (!country || loc.toLowerCase().includes(country.toLowerCase())) return loc;
  return `${loc}, ${country}`;
}

const TYPE_TAG: Record<string, { label: string; cls: string }> = {
  job: { label: "Job", cls: "bg-[#FBF0EC] text-[#9A3722]" },
  internship: { label: "Internship", cls: "bg-[#EEF6F7] text-[#0B6575]" },
  learnership: { label: "Learnership", cls: "bg-[#EDF6F0] text-[#1E6B40]" },
  graduate_programme: { label: "Graduate", cls: "bg-[#FDF3DC] text-[#7A5200]" },
  bursary: { label: "Bursary", cls: "bg-[#FDF3DC] text-[#7A5200]" },
};
export const typeTag = (t?: string) => TYPE_TAG[t || "job"] ?? TYPE_TAG.job;
