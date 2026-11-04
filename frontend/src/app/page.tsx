import type { Metadata } from "next";
import OpportunitiesTodayLink from "@/components/OpportunitiesTodayLink";
import JobAlertsLink from "@/components/JobAlertsLink";
import HomeExperience from "@/components/home/HomeExperience";
import { countryRows, snapshotStats } from "@/lib/landingStats";
import { coverageText } from "@/lib/regions";

export const metadata: Metadata = {
  description:
    "Ask about jobs, internships, learnerships, bursaries, graduate programmes and employers Sospana Sonke has stored, or about the Stats SA labour table. The answer includes the source and a clear note when the data is not there.",
};

/** Server-rendered headline. It is not inside the client bundle, so the first
 * paint does not wait for the rest of the homepage to hydrate. */
export default function HomePage() {
  const stats = snapshotStats();
  const coverage = coverageText(countryRows(stats.byCountry));
  return (
    <HomeExperience>
      <div className="ss-lcp grid min-w-0 grid-cols-[minmax(0,1fr)]">
        <a
          href="/game/play.html"
          className="group mt-4 flex max-w-xl items-center gap-4 rounded-2xl border-2 border-gold bg-gradient-to-r from-[#FFF8EC] to-white p-4 shadow-md transition hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#067589]"
        >
          <span aria-hidden="true" className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#067589] text-2xl">🎮</span>
          <span className="min-w-0 flex-1">
            <span className="block text-lg font-extrabold text-[#1F2328]">Play Gauteng Hustle Run</span>
            <span className="block text-sm text-[#4A4F57]">Free game. Run, collect coins, dodge obstacles. Works offline.</span>
          </span>
          <span className="shrink-0 rounded-full bg-[#A63A1E] px-4 py-2 text-sm font-bold text-white group-hover:bg-[#8A2F17]">Play now</span>
        </a>
        <OpportunitiesTodayLink className="mt-3 max-w-xl" />
        <JobAlertsLink className="mt-3 max-w-xl" />
        <h1 className="ss-intel-title mt-6 text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl">
          Discover what&apos;s possible.
          <br />
          <span className="ss-intel-accent">Understand what&apos;s changing.</span>
          <br />
          Act on what matters.
        </h1>
        <p className="ss-intel-lead mt-6 max-w-xl text-lg leading-relaxed">
          Sospana Sonke connects opportunities, data and intelligence to help people and businesses make
          better-informed decisions about South Africa&apos;s future.
        </p>
        <p className="ss-intel-lead mt-3 max-w-xl text-base leading-relaxed">
          South Africa is the featured country. Search, programmes and the labour table open there, and stored South African roles are listed first. Other countries stay in the directory.{" "}
          Pick any company in the list below to open its own careers page. Employers are listed across {coverage}. We do not promise you a place.
        </p>
        <noscript>
          <p className="ss-intel-lead mt-4 text-base">
            <a className="ss-intel-accent underline" href="/opportunities-today">
              See today's opportunities without JavaScript
            </a>
          </p>
        </noscript>
      </div>
    </HomeExperience>
  );
}
