import Link from "next/link";

export type CareersItem = { a: string; n: string; u: string };
export type CareersCat = { key: string; name: string; items: CareersItem[] };

/** Shared layout for /sa-careers and /countries/<slug>: header card, then collapsible category blocks. */
/* Reference palette, cycled per category block. Text colour picked for WCAG AA
   (white on teal/purple 4.9:1+; navy on coral/yellow 5.1:1+; white on green/blue
   3.6:1+, AA for the large bold summary text). Tint = pastel list bg. */
const BLOCK_COLOURS = [
  { bg: "bg-[#067589]", text: "text-white", tint: "bg-[#e3f3f5]", border: "border-[#067589]" },
  { bg: "bg-[#FD6948]", text: "text-[#07284C]", tint: "bg-[#ffeae4]", border: "border-[#FD6948]" },
  { bg: "bg-[#FCC033]", text: "text-[#07284C]", tint: "bg-[#fff6dc]", border: "border-[#FCC033]" },
  { bg: "bg-[#269958]", text: "text-white", tint: "bg-[#e3f4ea]", border: "border-[#269958]" },
  { bg: "bg-[#8450E4]", text: "text-white", tint: "bg-[#efe8fc]", border: "border-[#8450E4]" },
  { bg: "bg-[#1184F0]", text: "text-white", tint: "bg-[#e2f0fd]", border: "border-[#1184F0]" },
];

export default function CareersDirectory({ flag, title, cats }: { flag: string; title: string; cats: CareersCat[] }) {
  const shown = cats.filter((c) => c.items.length > 0);
  const total = shown.reduce((s, c) => s + c.items.length, 0);
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 text-[#07284C]">
      <div className="mb-5 rounded-2xl border-2 border-[#FCC033] bg-[#fff8e1] p-4">
        <h1 className="text-2xl font-extrabold sm:text-3xl">{flag} {title}</h1>
        {total > 0 ? (
          <p className="mt-1 text-base">
            While we&apos;re under maintenance, here are {total} direct careers links in {shown.length}{" "}
            {shown.length === 1 ? "category" : "categories"}, free for everyone, no login needed. Tap a name to open the
            employer&apos;s own careers page.
          </p>
        ) : (
          <p className="mt-1 text-base">
            No direct careers links yet for this country. We only list employers&apos; own careers pages that we have
            checked, and we&apos;re still adding them. This page is free for everyone, no login needed.
          </p>
        )}
        <Link href="/offline-guide" className="mt-3 inline-block rounded-xl border-2 border-[#FD6948] bg-[#FD6948] px-5 py-2 font-bold text-[#07284C] hover:bg-[#FCC033]">
          📘 Offline guide
        </Link>
      </div>
      <div className="space-y-3">
        {shown.map((c, i) => {
          const col = BLOCK_COLOURS[i % BLOCK_COLOURS.length];
          return (
          <details key={c.key} className={`rounded-2xl border-2 ${col.border} ${col.tint} shadow-sm`}>
            <summary className={`cursor-pointer select-none rounded-xl ${col.bg} px-4 py-3 text-lg font-extrabold ${col.text}`}>
              {c.name} <span>({c.items.length})</span>
            </summary>
            <ul className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3 lg:grid-cols-4">
              {c.items.map((it) => (
                <li key={it.u}>
                  <a
                    href={it.u}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={it.n}
                    className={`block rounded-xl border ${col.border} bg-white px-3 py-2 hover:bg-[#fff1c2]`}
                  >
                    <span className="block font-extrabold text-[#07284C] underline decoration-[#FCC033]">{it.a}</span>
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
