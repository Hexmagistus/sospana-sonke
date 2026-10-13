import type { Metadata } from "next";

const description =
  "Help keep Sospana Sonke free. It stores jobs, internships, learnerships, bursaries and graduate programmes, lists employers with a direct careers link, and shows the Stats SA labour table. A donation does not buy a place.";

export const metadata: Metadata = {
  title: "Support Sospana Sonke",
  description,
  alternates: { canonical: "/donate" },
  openGraph: { title: "Support Sospana Sonke · Sospana Sonke", description, url: "/donate" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
