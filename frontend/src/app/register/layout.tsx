import type { Metadata } from "next";
import { SITE_DESCRIPTION } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Create your free account",
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/register" },
  openGraph: { title: "Create your free account · Sospana Sonke", description: SITE_DESCRIPTION, url: "/register" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
