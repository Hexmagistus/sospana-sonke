import Link from "next/link";
import HomeExperience from "@/components/home/HomeExperience";
import { countryRows, snapshotStats } from "@/lib/landingStats";
import { coverageText } from "@/lib/regions";

/** Server-rendered headline. It is not inside the client bundle, so the first
 * paint does not wait for the rest of the homepage to hydrate. */
export default function HomePage() {
  const stats = snapshotStats();
  const coverage = coverageText(countryRows(stats.byCountry));
  return (
    <HomeExperience>
      <div className="ss-lcp grid min-w-0 grid-cols-[minmax(0,1fr)]">
        <h1 className="mt-6 text-4xl font-extrabold leading-[1.05] tracking-tight text-ss-text sm:text-6xl">
          Where talent meets
          <br />
          <span style={{ color: "#6b4700" }}>opportunity.</span>
        </h1>
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-ss-muted">
          First made for the SADC region, now listing employers across {coverage}. Each card is a direct
          link to that employer&apos;s own careers page. We do not host every vacancy, and we do not promise
          you the job. A card that says &ldquo;Not counted yet&rdquo; does not mean the employer has no vacancies:
          check their careers page directly.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/register"
            className="rounded-xl px-6 py-3.5 font-extrabold shadow-lg"
            style={{ background: "linear-gradient(120deg,#f5b301,#f59e0b)", color: "#3a2b00" }}
          >
            Create your free account
          </Link>
          <Link href="/companies" className="rounded-xl px-6 py-3.5 font-bold text-white" style={{ background: "#0b2447" }}>
            Browse companies
          </Link>
          <Link href="/jobs" className="rounded-xl border border-ss-border bg-ss-bg px-6 py-3.5 font-semibold text-ss-text">
            Search stored roles
          </Link>
        </div>
      </div>
    </HomeExperience>
  );
}
