import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SA_CAREERS_ENABLED } from "@/lib/maintenance";

// TEMPORARY maintenance guide, gated by SA_CAREERS_ENABLED (see src/lib/maintenance.ts).
export const metadata: Metadata = {
  title: "How to use Sospana Sonke offline during maintenance",
  description: "Simple steps to save Sospana Sonke on your phone and use it with no data while we upgrade.",
};

function Phone({ children }: { children: React.ReactNode }) {
  return (
    <svg viewBox="0 0 60 100" className="h-20 w-12 shrink-0" aria-hidden="true">
      <rect x="2" y="2" width="56" height="96" rx="9" fill="#07284C" />
      <rect x="7" y="12" width="46" height="74" rx="3" fill="#fff8e1" />
      <circle cx="30" cy="92" r="3" fill="#FCC033" />
      {children}
    </svg>
  );
}

function Section({ n, title, icon, children }: { n: number; title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-[#07284C]/15 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-3">
        {icon}
        <h2 className="text-lg font-extrabold sm:text-xl">
          <span className="mr-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#FCC033] text-[#07284C]">{n}</span>
          {title}
        </h2>
      </div>
      <div className="space-y-2 text-base leading-relaxed">{children}</div>
    </section>
  );
}

const ol = "list-decimal space-y-1 pl-6";

export default function OfflineGuidePage() {
  if (!SA_CAREERS_ENABLED) notFound();
  return (
    <main className="mx-auto max-w-3xl space-y-4 px-4 py-6 text-[#07284C]">
      <div className="rounded-2xl border-2 border-[#FCC033] bg-[#fff8e1] p-4">
        <h1 className="text-2xl font-extrabold sm:text-3xl">📘 How to use Sospana Sonke offline during maintenance</h1>
        <p className="mt-2">We&apos;re upgrading our servers. The site keeps working on your phone, even with no data. Follow these short steps.</p>
      </div>

      <Section n={1} title="Open the site once with data" icon={<Phone><path d="M20 40 l10-10 10 10 M30 30 v28" stroke="#07284C" strokeWidth="4" fill="none" /></Phone>}>
        <ol className={ol}>
          <li>Switch on data or Wi-Fi.</li>
          <li>Open <b>sospana-sonke.vercel.app</b> in Chrome (Android) or Safari (iPhone).</li>
          <li>Open the <Link href="/jobs" className="font-bold underline">jobs page</Link> and the <Link href="/sa-careers" className="font-bold underline">SA careers pages</Link> list.</li>
          <li>Wait a few seconds. Your phone now keeps a copy of the jobs page, the SA careers list, this guide and the login page.</li>
        </ol>
      </Section>

      <Section n={2} title="Add it to your home screen" icon={<Phone><rect x="14" y="22" width="14" height="14" rx="3" fill="#FCC033" /><rect x="32" y="22" width="14" height="14" rx="3" fill="#07284C" /><rect x="14" y="42" width="14" height="14" rx="3" fill="#07284C" /><path d="M39 44 v12 M33 50 h12" stroke="#FCC033" strokeWidth="4" /></Phone>}>
        <p className="font-bold">Android (Chrome):</p>
        <ol className={ol}>
          <li>Tap the <b>⋮</b> menu at the top right.</li>
          <li>Tap <b>Add to Home screen</b> or <b>Install app</b>.</li>
          <li>Tap <b>Add</b> or <b>Install</b>.</li>
        </ol>
        <p className="font-bold">iPhone (Safari):</p>
        <ol className={ol}>
          <li>Tap the <b>Share</b> button (square with an arrow).</li>
          <li>Scroll and tap <b>Add to Home Screen</b>.</li>
          <li>Tap <b>Add</b>.</li>
        </ol>
      </Section>

      <Section n={3} title="Open it with no signal" icon={<Phone><path d="M18 60 a17 17 0 0 1 24 0 M23 66 a9 9 0 0 1 14 0" stroke="#07284C" strokeWidth="4" fill="none" /><path d="M16 30 L44 70" stroke="#c62828" strokeWidth="4" /></Phone>}>
        <ol className={ol}>
          <li>Tap the Sospana Sonke icon on your home screen.</li>
          <li>If you see <b>&quot;You&apos;re offline&quot;</b>, tap <b>Stored roles</b> to open the saved jobs.</li>
          <li>Pages you opened before will open from your phone.</li>
        </ol>
      </Section>

      <Section n={4} title="What the offline banner means" icon={<svg viewBox="0 0 60 40" className="h-12 w-16 shrink-0" aria-hidden="true"><rect width="60" height="40" rx="6" fill="#07284C" /><rect x="6" y="14" width="48" height="12" rx="3" fill="#FCC033" /></svg>}>
        <p>On the jobs page you may see <b>&quot;Offline – showing jobs saved on 20 Oct 2026&quot;</b> (with your own date).</p>
        <p>It means you&apos;re seeing the list your phone saved on that day. New jobs show up the next time you open the page with data.</p>
        <p>✅ <b>Expired jobs are hidden automatically.</b> If a closing date has passed, that job disappears from the saved list, even offline.</p>
      </Section>

      <Section n={5} title="Use the SA careers pages list" icon={<svg viewBox="0 0 60 50" className="h-12 w-16 shrink-0" aria-hidden="true"><rect width="60" height="12" rx="4" fill="#07284C" /><rect y="19" width="60" height="12" rx="4" fill="#07284C" /><rect y="38" width="60" height="12" rx="4" fill="#FCC033" /></svg>}>
        <ol className={ol}>
          <li>Open <Link href="/sa-careers" className="font-bold underline">SA careers pages</Link>.</li>
          <li>Tap a category, for example <b>Universities</b> or <b>Municipalities</b>, to open it.</li>
          <li>Each employer is shown by its short name, like <b>UCT</b> or <b>SANParks</b>. The full name is underneath.</li>
          <li>Tap a name to open that employer&apos;s own careers page in a new tab.</li>
        </ol>
        <p>📶 The list works offline, but employer websites need data to open.</p>
      </Section>

      <Section n={6} title="Login and sign-up are paused" icon={<svg viewBox="0 0 50 50" className="h-12 w-12 shrink-0" aria-hidden="true"><rect x="8" y="22" width="34" height="24" rx="5" fill="#07284C" /><path d="M15 22 v-7 a10 10 0 0 1 20 0 v7" stroke="#07284C" strokeWidth="5" fill="none" /><circle cx="25" cy="34" r="4" fill="#FCC033" /></svg>}>
        <p>While we upgrade, you can&apos;t log in or create an account. You don&apos;t need one to view jobs or the SA careers list. Your account will be back after maintenance.</p>
      </Section>

      <Section n={7} title="Tips to save data" icon={<svg viewBox="0 0 50 50" className="h-12 w-12 shrink-0" aria-hidden="true"><circle cx="25" cy="25" r="22" fill="#FCC033" /><text x="25" y="33" textAnchor="middle" fontSize="22" fontWeight="bold" fill="#07284C">R</text></svg>}>
        <ul className="list-disc space-y-1 pl-6">
          <li>Open the site on free Wi-Fi when you can (library, school, work).</li>
          <li>Browse the saved list offline, and only use data to open the employer pages you want to apply to.</li>
          <li>Don&apos;t clear your browser data or cache, or your saved copy is deleted.</li>
        </ul>
      </Section>

      <Section n={8} title="Come back daily with data" icon={<svg viewBox="0 0 50 50" className="h-12 w-12 shrink-0" aria-hidden="true"><path d="M40 25 a15 15 0 1 1 -5 -11" stroke="#07284C" strokeWidth="5" fill="none" /><path d="M36 6 v10 h-10" stroke="#FCC033" strokeWidth="5" fill="none" /></svg>}>
        <p>Once a day, open the jobs page with data for a few seconds. Your phone saves the newest list, ready for when you&apos;re offline again.</p>
      </Section>

      <div className="flex flex-wrap gap-3 pb-4">
        <Link href="/sa-careers" className="rounded-xl border-2 border-[#FCC033] bg-white px-5 py-3 font-extrabold">🇿🇦 SA careers pages</Link>
      </div>
    </main>
  );
}
