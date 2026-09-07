import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Verified employers across Africa",
  description: "Browse 2,400+ verified employers across 26 African markets — companies, state-owned enterprises, government departments and municipalities — and apply directly on their official careers pages.",
  alternates: { canonical: "/companies" },
  openGraph: { title: "Verified employers across Africa · Sospana Sonke", description: "Browse 2,400+ verified employers across 26 African markets — companies, state-owned enterprises, government departments and municipalities — and apply directly on their official careers pages.", url: "/companies" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
