import type { Metadata } from "next";

const description =
  "Help keep Sospana Sonke free. It started in the SADC region and lists employers with a direct careers link across Africa, Oceania, Europe, South America, North America and Asia. A donation does not buy a job.";

export const metadata: Metadata = {
  title: "Support Sospana Sonke",
  description,
  alternates: { canonical: "/donate" },
  openGraph: { title: "Support Sospana Sonke · Sospana Sonke", description, url: "/donate" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
