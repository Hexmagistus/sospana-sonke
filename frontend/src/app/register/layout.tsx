import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create your free account",
  description: "Join Sospana Sonke free — discover verified employers across Africa and apply directly on their official careers pages.",
  alternates: { canonical: "/register" },
  openGraph: { title: "Create your free account · Sospana Sonke", description: "Join Sospana Sonke free — discover verified employers across Africa and apply directly on their official careers pages.", url: "/register" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
