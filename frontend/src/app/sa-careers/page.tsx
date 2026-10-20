import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import data from "@/data/saCareers.json";
import { SA_CAREERS_ENABLED } from "@/lib/maintenance";

// TEMPORARY: maintenance-mode directory, gated by SA_CAREERS_ENABLED (see src/lib/maintenance.ts).
export const metadata: Metadata = {
  title: "South African careers pages | Sospana Sonke",
  description: "Direct careers links for South African employers, open to everyone during maintenance.",
};

type Item = { a: string; n: string; u: string };
type Cat = { key: string; name: string; items: Item[] };

export default function SaCareersPage() {
  if (!SA_CAREERS_ENABLED) notFound();
  const cats = (data as { categories: Cat[] }).categories;
  const total = cats.reduce((s, c) => s + c.items.length, 0);
  return (
    <main className="mx-auto max-w-5xl px-4 py-6 text-[#0b2447]">
      <div className="mb-5 rounded-2xl border-2 border-[#f5b301] bg-[#fff8e1] p-4">
        <h1 className="text-2xl font-extrabold sm:text-3xl">🇿🇦 South African careers pages</h1>
        <p className="mt-1 text-base">
          While we&apos;re under maintenance, here are {total} direct careers links in {cats.length} categories, free
          for everyone, no login needed. Tap a name to open the employer&apos;s own careers page.
        </p>
        <Link href="/jobs" className="mt-3 inline-block rounded-xl bg-[#0b2447] px-5 py-2 font-bold text-[#f5b301]">
          ← Browse jobs
        </Link>
        <Link href="/offline-guide" className="ml-2 mt-3 inline-block rounded-xl border-2 border-[#f5b301] bg-white px-5 py-2 font-bold">
          📘 Offline guide
        </Link>
      </div>
      <div className="space-y-3">
        {cats.map((c) => (
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
