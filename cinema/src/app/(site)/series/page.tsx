import type { Metadata } from "next";
import { CategoryBody } from "@/components/category-body";
import { getPublicCatalog } from "@/lib/public-catalog";

export const metadata: Metadata = {
  title: "Series",
  description: "Series with a verified licence.",
  alternates: { canonical: "/series" },
};

export default async function SeriesPage() {
  const catalog = await getPublicCatalog();
  return <CategoryBody catalog={catalog} slug="tv-series" />;
}
