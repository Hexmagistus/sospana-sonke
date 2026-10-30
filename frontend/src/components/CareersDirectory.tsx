import Link from "next/link";
import OpportunitiesTodayLink from "./OpportunitiesTodayLink";
import JobAlertsLink from "./JobAlertsLink";
import { WhatsAppIcon } from "./WhatsAppChannel";
import { WHATSAPP_CHANNEL_URL } from "@/lib/social";
import { createHash } from "node:crypto";

// Invisible per-page fingerprint: a stable token unique to each directory page, carried in
// data attributes only (no visible text, no fake entries). Lets a copied page be traced back.
export function watermark(key: string): string {
  return "ssk-" + createHash("sha256").update(`sospana-sonke-wm-2026:${key}`).digest("hex").slice(0, 16);
}

export type CareersItem = { a: string; n: string; u: string };
export type CareersCat = { key: string; name: string; items: CareersItem[] };

/** Shared layout for /sa-careers and /countries/<slug>: header card, then collapsible category blocks. */
/* Corporate palette: deeper, calmer tones of the reference colours, cycled per
   category block. Each block is a white card with a coloured left accent bar,
   a soft tinted header and a solid count pill. Pill text contrast (WCAG AA):
   white on teal 6.7, coral 5.4, green 5.3, purple 6.5, blue 5.9; navy on gold 7.3. */
const BLOCK_COLOURS = [
  { bar: "border-l-[#0B6575]", pill: "bg-[#0B6575] text-white", tint: "bg-[#EEF6F7]", link: "hover:border-[#0B6575]" },
  { bar: "border-l-[#B8432A]", pill: "bg-[#B8432A] text-white", tint: "bg-[#FBF0EC]", link: "hover:border-[#B8432A]" },
  { bar: "border-l-[#E2AE3C]", pill: "bg-[#E2AE3C] text-[#07284C]", tint: "bg-[#FDF7E7]", link: "hover:border-[#E2AE3C]" },
  { bar: "border-l-[#1E7A47]", pill: "bg-[#1E7A47] text-white", tint: "bg-[#EDF6F0]", link: "hover:border-[#1E7A47]" },
  { bar: "border-l-[#6B44C2]", pill: "bg-[#6B44C2] text-white", tint: "bg-[#F3EFFB]", link: "hover:border-[#6B44C2]" },
  { bar: "border-l-[#1F64B5]", pill: "bg-[#1F64B5] text-white", tint: "bg-[#EDF3FB]", link: "hover:border-[#1F64B5]" },
];

export default function CareersDirectory({ flag, title, cats, wmKey }: { flag: string; title: string; cats: CareersCat[]; wmKey: string }) {
  const shown = cats.filter((c) => c.items.length > 0);
  const total = shown.reduce((s, c) => s + c.items.length, 0);
  const wm = watermark(wmKey);
  return (
    <main data-ss-wm={wm} data-ss-owner="Sospana Sonke" className="mx-auto max-w-5xl px-4 py-8 font-sans text-[#07284C] sm:px-6">
      <div className="mb-6 rounded-lg border border-[#07284C]/10 border-t-4 border-t-[#E2AE3C] bg-white p-5 shadow-sm sm:p-6">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{flag} {title}</h1>
        {total > 0 ? (
          <p className="mt-2 max-w-3xl text-base leading-relaxed text-slate-700">
            While we&apos;re under maintenance, here are {total} direct careers links in {shown.length}{" "}
            {shown.length === 1 ? "category" : "categories"}, free for everyone, no login needed. Tap a name to open the
            employer&apos;s own careers page.
          </p>
        ) : (
          <p className="mt-2 max-w-3xl text-base leading-relaxed text-slate-700">
            No direct careers links yet for this country. We only list employers&apos; own careers pages that we have
            checked, and we&apos;re still adding them. This page is free for everyone, no login needed.
          </p>
        )}
        <Link href="/offline-guide" className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#B8432A] px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#9A3722] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07284C] motion-reduce:transition-none">
          📘 Offline guide
        </Link>
        <a
          href={WHATSAPP_CHANNEL_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-3 mt-4 inline-flex items-center gap-2 rounded-md bg-[#25D366] px-4 py-2 text-sm font-semibold text-[#07284C] shadow-sm transition-colors hover:bg-[#1EBE5A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07284C] motion-reduce:transition-none"
        >
          <WhatsAppIcon className="h-4 w-4" /> Join our WhatsApp channel
        </a>
      </div>
      {wmKey === "sa-careers" && <OpportunitiesTodayLink className="mb-4" />}
      {wmKey === "sa-careers" && <JobAlertsLink className="mb-6" />}
      <div className="space-y-4">
        {shown.map((c, i) => {
          const col = BLOCK_COLOURS[i % BLOCK_COLOURS.length];
          return (
          <details key={c.key} className={`group overflow-hidden rounded-lg border border-[#07284C]/10 border-l-[6px] ${col.bar} bg-white shadow-sm`}>
            <summary className={`flex cursor-pointer select-none items-center justify-between gap-3 ${col.tint} px-5 py-3.5 text-base font-semibold tracking-tight text-[#07284C] sm:text-lg`}>
              <span>{c.name}</span> <span className={`rounded-full px-2.5 py-0.5 text-sm font-semibold tabular-nums ${col.pill}`}>({c.items.length})</span>
            </summary>
            <ul className="grid grid-cols-2 gap-3 border-t border-[#07284C]/10 p-4 sm:grid-cols-3 lg:grid-cols-4">
              {c.items.map((it) => (
                <li key={it.u}>
                  <a
                    href={it.u}
                    data-ss-ref={wm}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={it.n}
                    className={`block rounded-md border border-[#07284C]/12 bg-white px-3 py-2 transition-colors ${col.link} hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#07284C] motion-reduce:transition-none`}
                  >
                    <span className="block font-semibold text-[#07284C]">{it.a}</span>
                    <span className="block truncate text-xs text-slate-700">{it.n}</span>
                  </a>
                </li>
              ))}
            </ul>
          </details>
          );
        })}
      </div>
    </main>
  );
}
