import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Directory coverage map",
  description: "How complete is the Sospana Sonke directory, honestly — verified working links, links still pending verification, and links that need attention, by country and category.",
  alternates: { canonical: "/coverage" },
  openGraph: { title: "Directory coverage map · Sospana Sonke", description: "How complete is the Sospana Sonke directory, honestly — by country and category.", url: "/coverage" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
