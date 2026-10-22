import type { Metadata } from "next";
import { notFound } from "next/navigation";
import data from "@/data/saCareers.json";
import { SA_CAREERS_ENABLED } from "@/lib/maintenance";
import CareersDirectory, { type CareersCat } from "@/components/CareersDirectory";

// TEMPORARY: maintenance-mode directory, gated by SA_CAREERS_ENABLED (see src/lib/maintenance.ts).
export const metadata: Metadata = {
  title: "South African careers pages | Sospana Sonke",
  description: "Direct careers links for South African employers, open to everyone during maintenance.",
};

export default function SaCareersPage() {
  if (!SA_CAREERS_ENABLED) notFound();
  const cats = (data as { categories: CareersCat[] }).categories;
  return <CareersDirectory flag="🇿🇦" title="South African careers pages" cats={cats} wmKey="sa-careers" />;
}
