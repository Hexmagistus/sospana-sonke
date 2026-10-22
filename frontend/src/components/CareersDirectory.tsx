import Link from "next/link";

export type CareersItem = { a: string; n: string; u: string };
export type CareersCat = { key: string; name: string; items: CareersItem[] };

/** Shared layout for /sa-careers and /countries/<slug>: header card, then collapsible category blocks. */
export default function CareersDirectory({ flag, title, cats }: { flag: string; title: string; cats: CareersCat[] }) {
  const shown = cats.filter((c) => c.items.length > 0);
  const total = shown.reduce((s, c) => s + c.items.length, 0);
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 text-[#0b2447]">
      <div className="mb-5 rounded-2xl border-2 border-[#f5b301] bg-[#fff8e1] p-4">
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
        <Link href="/jobs" className="mt-3 inline-block rounded-xl bg-[#0b2447] px-5 py-2 font-bold text-[#f5b301]">
          ← Browse jobs
        </Link>
        <Link href="/offline-guide" className="ml-2 mt-3 inline-block rounded-xl border-2 border-[#f5b301] bg-white px-5 py-2 font-bold">
          📘 Offline guide
        </Link>
      </div>
      <div className="space-y-3">
        {shown.map((c) => (
          <details key={c.key} className="rounded-2xl border border-[#0b2447]/20 bg-white shadow-sm">
            <summary className="cursor-pointer select-none rounded-2xl bg-[#0b2447] px-4 py-3 text-lg font-extrabold text-white">
              {c.name} <span className="text-[#f5b301]">({c.items.length})</span>
            </summary>
            <ul className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3 lg:grid-cols-4">
              {c.items.map((it) => (
                <li key={it.u}>
                  <a
                    href={it.u}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={it.n}
                    className="block rounded-xl border border-[#f5b301]/60 bg-[#fffdf5] px-3 py-2 hover:bg-[#fff1c2]"
                  >
                    <span className="block font-extrabold text-[#0b2447] underline decoration-[#f5b301]">{it.a}</span>
                    <span className="block truncate text-xs text-slate-600">{it.n}</span>
                  </a>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </main>
  );
}
