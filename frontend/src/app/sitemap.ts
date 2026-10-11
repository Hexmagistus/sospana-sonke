import type { MetadataRoute } from "next";
import { publicCountries } from "@/lib/countryPageData";
import { SNAPSHOT_AS_OF } from "@/lib/landingStats";
import { SITE_URL } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const snapshotDate = new Date(`${SNAPSHOT_AS_OF}T00:00:00.000Z`);
  const entry = (
    path: string,
    priority: number,
    changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"],
  ) => ({
    url: `${SITE_URL}${path === "/" ? "" : path}`,
    lastModified: now,
    changeFrequency,
    priority,
  });

  const countries = publicCountries().map((row) => ({
    url: `${SITE_URL}/countries/${row.slug}`,
    lastModified: snapshotDate,
    changeFrequency: "weekly" as const,
    priority: 0.7,
  }));

  return [
    entry("/", 1.0, "weekly"),
    // /companies requires login (<Guard>) -- not listed here since a crawler
    // would just hit a login redirect; see robots.ts's disallow list.
    // /countries is public: one page per country in the built-in snapshot.
    entry("/countries", 0.8, "weekly"),
    ...countries,
    entry("/donate", 0.5, "monthly"),
    entry("/login", 0.6, "monthly"),
    entry("/register", 0.6, "monthly"),
    entry("/forgot-password", 0.3, "yearly"),
    entry("/reset-password", 0.3, "yearly"),
    entry("/privacy", 0.3, "yearly"),
    entry("/terms", 0.3, "yearly"),
  ];
}
