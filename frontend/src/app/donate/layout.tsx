import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Support Sospana Sonke",
  description: "Help keep Sospana Sonke free for job seekers across Africa.",
  alternates: { canonical: "/donate" },
  openGraph: { title: "Support Sospana Sonke · Sospana Sonke", description: "Help keep Sospana Sonke free for job seekers across Africa.", url: "/donate" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
