import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Job vacancies across Africa",
  description: "Explore real vacancies from verified employers across Africa and apply directly on their official careers pages — no middleman job boards.",
  alternates: { canonical: "/jobs" },
  openGraph: { title: "Job vacancies across Africa · Sospana Sonke", description: "Explore real vacancies from verified employers across Africa and apply directly on their official careers pages — no middleman job boards.", url: "/jobs" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
