import type { Metadata } from "next";
import { SITE_DESCRIPTION } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Sign in",
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/login" },
  openGraph: { title: "Sign in · Sospana Sonke", description: SITE_DESCRIPTION, url: "/login" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
