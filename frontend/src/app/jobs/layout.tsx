import type { Metadata } from "next";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

const description =
  "Search jobs, internships, learnerships, bursaries and graduate programmes Sospana Sonke has already read from official pages. Filter by country, employer, keyword and how recently the role was seen. Apply on the source page.";

// The list streams in after the heading. The metadata API then inserts the
// description after the first head, which a lab check can miss. These tags
// are part of the layout shell.
export const metadata: Metadata = {
  title: "Open roles the scanner has stored",
  description,
  alternates: { canonical: "/jobs" },
  openGraph: {
    title: `Open roles · ${SITE_NAME}`,
    description: "Stored openings of every type. A missing role here does not mean the organisation has nothing open.",
    url: "/jobs",
  },
};

export default function JobsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <title>{`Open roles the scanner has stored · ${SITE_NAME}`}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={`${SITE_URL}/jobs`} />
      {children}
    </>
  );
}
