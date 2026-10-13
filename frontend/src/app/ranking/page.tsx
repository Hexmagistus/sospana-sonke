import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How ranking works",
  description:
    "Stored roles keep their own order. A sponsored row is labelled, capped, and shown only when it matches the filters.",
  alternates: { canonical: "/ranking" },
};

export default function RankingPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-4">
      <header className="space-y-2">
        <p className="text-sm font-semibold text-ss-primary">Ranking</p>
        <h1 className="font-display text-3xl font-bold text-ss-text">How ranking works</h1>
      </header>
      <div className="ss-card space-y-3 text-sm leading-relaxed text-ss-text">
        <p>
          Open roles are the rows the scanner has stored, or an opportunity an organisation submitted and an
          administrator approved. South Africa is listed first when no country is selected. After that, the jobs
          page uses the date the row was last seen, and the opportunities page can use a closing date the source
          stated. Choosing a country shows that country only.
        </p>
        <p>
          A featured listing is a paid placement of one approved opportunity for a set number of days. It appears in
          a separate list labelled <strong>Sponsored</strong>. It is included only when it matches the filters on
          that page. Each results page shows at most two sponsored rows.
        </p>
        <p>
          The sponsored list does not move the other rows. A role that is not sponsored keeps the place its date
          gives it. There is no countdown and no claim that a place is about to run out.
        </p>
        <p>
          An opportunity posted by the organisation is labelled <strong>Employer-submitted</strong> after it is
          approved. It is not listed while it is waiting for that check.
        </p>
        <p>
          Job seekers do not pay to search, to open a source link, to save an alert, or to use the CV tools.
        </p>
      </div>
      <p className="text-sm text-ss-muted">
        <Link href="/jobs" className="font-semibold text-navy underline">Jobs</Link>
        {" · "}
        <Link href="/pricing" className="font-semibold text-navy underline">Pricing</Link>
        {" · "}
        <Link href="/terms" className="font-semibold text-navy underline">Terms</Link>
      </p>
    </article>
  );
}
