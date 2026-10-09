import type { Metadata } from "next";
import { snapshotDirectoryDescription } from "@/lib/landingStats";

const description = snapshotDirectoryDescription();

export const metadata: Metadata = {
  title: "Employers with a direct careers link",
  description,
  alternates: { canonical: "/companies" },
  openGraph: { title: "Employers with a direct careers link · Sospana Sonke", description, url: "/companies" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
