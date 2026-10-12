import type { MetadataRoute } from "next";
import { publicCountries } from "@/lib/countryPageData";
import { employerPath } from "@/lib/employerPage";
import { SNAPSHOT_AS_OF } from "@/lib/landingStats";
import { SITE_URL } from "@/lib/seo";

export const revalidate = 3600;

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

/** Employer URLs for rows that have a careers link. An unreachable API adds none. */
async function employerEntries(modified: Date): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  const limit = 200;
  for (let offset = 0; offset < 20000; offset += limit) {
    try {
      const res = await fetch(`${API}/employers?limit=${limit}&offset=${offset}`, { next: { revalidate: 3600 } });
      if (!res.ok) break;
      const data = (await res.json()) as { employers?: { id?: string }[] };
      const rows = Array.isArray(data.employers) ? data.employers : [];
      for (const row of rows) {
        if (!row?.id) continue;
        entries.push({
          url: `${SITE_URL}${employerPath(row.id)}`,
          lastModified: modified,
          changeFrequency: "weekly",
          priority: 0.6,
        });
      }
      if (rows.length < limit) break;
    } catch {
      break;
    }
  }
  return entries;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
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
    entry("/jobs", 0.9, "daily"),
    // /companies requires login (<Guard>) -- not listed here since a crawler
    // would just hit a login redirect; see robots.ts's disallow list.
    // /countries is public: one page per country in the built-in snapshot.
    entry("/countries", 0.8, "weekly"),
    ...countries,
    entry("/employers", 0.8, "daily"),
    ...await employerEntries(snapshotDate),
    entry("/donate", 0.5, "monthly"),
    entry("/login", 0.6, "monthly"),
    entry("/register", 0.6, "monthly"),
    entry("/forgot-password", 0.3, "yearly"),
    entry("/reset-password", 0.3, "yearly"),
    entry("/privacy", 0.3, "yearly"),
    entry("/terms", 0.3, "yearly"),
  ];
}
