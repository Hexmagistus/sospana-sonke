import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CategoryBody } from "@/components/category-body";
import { getPublicCatalog } from "@/lib/public-catalog";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  const category = catalog.categories.find((item) => item.slug === slug);
  if (!category) return { title: "Category" };
  return {
    title: category.name,
    description: category.description,
    alternates: { canonical: `/categories/${category.slug}` },
  };
}

export default async function CategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const catalog = await getPublicCatalog();
  if (!catalog.categories.some((item) => item.slug === slug)) notFound();
  return <CategoryBody catalog={catalog} slug={slug} />;
}
