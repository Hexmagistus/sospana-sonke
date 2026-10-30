import type { Metadata } from "next";
import Link from "next/link";
import data from "@/data/opportunitiesToday.json";
import { WhatsAppIcon } from "@/components/WhatsAppChannel";
import { WHATSAPP_CHANNEL_URL } from "@/lib/social";

// Static data (no database/backend). Re-rendered hourly so posts whose closing date has passed drop off.
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Opportunities found today | Sospana Sonke",
  description: "Open posts at South African public employers, checked on their official careers pages. Free, no login.",
};

type Post = { employer: string; title: string; location: string | null; closingDate: string | null; url: string };

const BLOCK_COLOURS = [
  { bar: "border-l-[#0B6575]", pill: "bg-[#0B6575] text-white", tint: "bg-[#EEF6F7]", link: "hover:border-[#0B6575]" },
  { bar: "border-l-[#B8432A]", pill: "bg-[#B8432A] text-white", tint: "bg-[#FBF0EC]", link: "hover:border-[#B8432A]" },
  { bar: "border-l-[#E2AE3C]", pill: "bg-[#E2AE3C] text-[#07284C]", tint: "bg-[#FDF7E7]", link: "hover:border-[#E2AE3C]" },
  { bar: "border-l-[#1E7A47]", pill: "bg-[#1E7A47] text-white", tint: "bg-[#EDF6F0]", link: "hover:border-[#1E7A47]" },
  { bar: "border-l-[#07284C]", pill: "bg-[#07284C] text-white", tint: "bg-[#EEF1F6]", link: "hover:border-[#07284C]" },
];

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
function fmt(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}
/** Today's date in South Africa (UTC+2, no DST) as YYYY-MM-DD. */
function todaySA() {
  return new Date(Date.now() + 2 * 3600 * 1000).toISOString().slice(0, 10);
}

export default function OpportunitiesTodayPage() {
  const today = todaySA();
  const posts = (data as { date: string; posts: Post[] }).posts.filter((p) => !p.closingDate || p.closingDate >= today);
  const groups: { employer: string; posts: Post[] }[] = [];
  for (const p of posts) {
    let g = groups.find((x) => x.employer === p.employer);
    if (!g) groups.push((g = { employer: p.employer, posts: [] }));
    g.posts.push(p);
  }
  return (
    <main className="min-h-screen bg-[#FBF6EC]">
      <div className="mx-auto max-w-5xl px-4 py-8 font-sans text-[#07284C] sm:px-6">
        <div className="mb-6 rounded-lg border border-[#07284C]/10 border-t-4 border-t-[#E2AE3C] bg-white p-5 shadow-sm sm:p-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-[#B8432A]">30 October 2026</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">🇿🇦 Opportunities found today</h1>
          <p className="mt-2 max-w-3xl text-base leading-relaxed text-slate-700">
            {posts.length > 0 ? (
              <>
                <strong className="text-[#07284C]">{posts.length} open posts</strong> at {groups.length}{" "}
                {groups.length === 1 ? "employer" : "employers"}, each checked on the employer&apos;s official careers page.
                Posts drop off automatically once their closing date has passed. Free for everyone, no login needed. Apply
                only on the official links.
              </>
            ) : (
              <>All of today&apos;s posts have closed. Check back soon, or see the SA careers pages.</>
            )}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/sa-careers" className="inline-flex items-center gap-2 rounded-md bg-[#07284C] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#0B3A6B] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07284C]">
              🇿🇦 SA careers pages
            </Link>
            <a
              href={WHATSAPP_CHANNEL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-md bg-[#25D366] px-4 py-2 text-sm font-semibold text-[#07284C] shadow-sm transition-colors hover:bg-[#1EBE5A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07284C] motion-reduce:transition-none"
            >
              <WhatsAppIcon className="h-4 w-4" /> Join our WhatsApp channel
            </a>
          </div>
        </div>
        <div className="space-y-4">
          {groups.map((g, i) => {
            const col = BLOCK_COLOURS[i % BLOCK_COLOURS.length];
            return (
              <section key={g.employer} className={`overflow-hidden rounded-lg border border-[#07284C]/10 border-l-[6px] ${col.bar} bg-white shadow-sm`}>
                <h2 className={`flex items-center justify-between gap-3 ${col.tint} px-5 py-3.5 text-base font-semibold tracking-tight sm:text-lg`}>
                  <span>{g.employer}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-sm font-semibold tabular-nums ${col.pill}`}>({g.posts.length})</span>
                </h2>
                <ul className="grid gap-3 border-t border-[#07284C]/10 p-4 sm:grid-cols-2">
                  {g.posts.map((p) => (
                    <li key={p.url + p.title}>
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`block h-full rounded-md border border-[#07284C]/12 bg-white px-3 py-2.5 transition-colors ${col.link} hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#07284C] motion-reduce:transition-none`}
                      >
                        <span className="block font-semibold text-[#07284C]">{p.title}</span>
                        {p.location && <span className="mt-0.5 block text-sm text-slate-700">📍 {p.location}</span>}
                        <span className="mt-0.5 block text-sm font-medium text-[#B8432A]">
                          {p.closingDate ? `Closes ${fmt(p.closingDate)}` : "Open – no closing date shown"}
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
        <p className="mt-6 text-sm text-slate-700">Apply only on the official links ✅ Free for all job seekers 💼</p>
      </div>
    </main>
  );
}
