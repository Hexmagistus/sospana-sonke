import type { MetadataRoute } from "next";
import { getPublicCatalog } from "@/lib/public-catalog";
import { siteUrl } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const catalog = await getPublicCatalog();
  const base = siteUrl();
  const staticPaths = ["", "/movies", "/kids", "/kids/preschool", "/kids/6-8", "/kids/9-12", "/kids/family", "/series", "/search", "/categories", "/takedown", "/privacy", "/terms"];
  const categories = catalog.categories.map((category) => `/categories/${category.slug}`);
  const movies = catalog.movies.filter((movie) => movie.published).map((movie) => `/movies/${movie.slug}`);
  return [...staticPaths, ...categories, ...movies].map((path) => ({
    url: `${base}${path || "/"}`,
    changeFrequency: "weekly" as const,
    priority: path === "" ? 1 : 0.7,
  }));
}
