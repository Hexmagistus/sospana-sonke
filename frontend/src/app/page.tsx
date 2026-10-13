import type { Metadata } from "next";
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
          Ask in the box below. The answer uses jobs, internships, learnerships, bursaries and graduate
          programmes the scanner has stored, employers in the directory, and the Stats SA labour table, with
          the source and the date we last saw them. Employers are listed across {coverage}. If the data is
          not there, the answer says so. We do not promise you a place.
        </p>
        <noscript>
          <p className="ss-intel-lead mt-4 text-base">
            <a className="ss-intel-accent underline" href="/jobs">
              Search stored roles without JavaScript
            </a>
          </p>
        </noscript>
      </div>
    </HomeExperience>
  );
}
