import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Sospana Sonke collects, uses and protects your personal information.",
  alternates: { canonical: "/privacy" },
  openGraph: { title: "Privacy Policy · Sospana Sonke", description: "How Sospana Sonke collects, uses and protects your personal information.", url: "/privacy" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
