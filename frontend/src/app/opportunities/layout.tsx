import type { Metadata } from "next";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

const description =
  "Internships, learnerships, bursaries and graduate programmes Sospana Sonke has stored from official pages. A closing date is shown only when the source stated one. Jobs are in the same store.";

export const metadata: Metadata = {
  title: "Internships, learnerships, bursaries and graduate programmes",
  description,
  alternates: { canonical: "/opportunities" },
  openGraph: {
    title: `Opportunities · ${SITE_NAME}`,
    description: "Stored programmes, with the type, the organisation, the source link and the last checked date.",
    url: "/opportunities",
  },
};

export default function OpportunitiesLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <title>{`Internships, learnerships, bursaries and graduate programmes · ${SITE_NAME}`}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={`${SITE_URL}/opportunities`} />
      {children}
    </>
  );
}
