import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms that govern your use of Sospana Sonke.",
  alternates: { canonical: "/terms" },
  openGraph: { title: "Terms of Service · Sospana Sonke", description: "The terms that govern your use of Sospana Sonke.", url: "/terms" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
