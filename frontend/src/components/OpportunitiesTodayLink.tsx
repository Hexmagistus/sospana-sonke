import Link from "next/link";

/** Prominent block linking to /opportunities-today (bright light card, gold top bar). */
export default function OpportunitiesTodayLink({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/opportunities-today"
      className={`block rounded-lg border border-[#07284C]/10 border-l-[6px] border-l-[#1E7A47] bg-[#FFF8EC] p-4 text-[#07284C] shadow-sm transition-colors hover:bg-[#FDF7E7] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#07284C] motion-reduce:transition-none ${className}`}
    >
      <span className="block text-base font-bold tracking-tight sm:text-lg">🆕 Opportunities found today →</span>
      <span className="mt-1 block text-sm text-slate-700">
        Open posts at DBSA, SANRAL, Armscor, Wits and TUT, checked on their official pages. Free, no login.
      </span>
    </Link>
  );
}
