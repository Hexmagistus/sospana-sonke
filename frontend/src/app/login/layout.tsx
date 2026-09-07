import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to Sospana Sonke to build your profile and apply directly to verified employers across Africa.",
  alternates: { canonical: "/login" },
  openGraph: { title: "Sign in · Sospana Sonke", description: "Sign in to Sospana Sonke to build your profile and apply directly to verified employers across Africa.", url: "/login" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
