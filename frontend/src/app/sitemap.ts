import type { MetadataRoute } from "next";
import { unstable_cache } from "next/cache";
import { publicCountries } from "@/lib/countryPageData";
import { employerPath } from "@/lib/employerPage";
import { SNAPSHOT_AS_OF } from "@/lib/landingStats";
import { SITE_URL } from "@/lib/seo";

// The build can finish before Frankfurt is serving /employers. A static sitemap
// would then keep the empty employer list for an hour. This route is rendered
// on request. A successful id list is cached; a failed fetch is not.
export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

async function fetchEmployerIds(): Promise<string[]> {
  const ids: string[] = [];
  const limit = 5000;
  for (let offset = 0; offset < 20000; offset += limit) {
    const res = await fetch(`${API}/employers/ids?limit=${limit}&offset=${offset}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`employers ${res.status}`);
    const data = (await res.json()) as { ids?: unknown; matched?: unknown };
    const rows = Array.isArray(data.ids) ? data.ids.filter((id): id is string => typeof id === "string" && id.length > 0) : [];
    ids.push(...rows);
    const matched = typeof data.matched === "number" ? data.matched : ids.length;
    if (rows.length < limit || ids.length >= matched) break;
  }
  return ids;
}

const cachedEmployerIds = unstable_cache(fetchEmployerIds, ["public-employer-sitemap-ids"], { revalidate: 3600 });

/** Employer URLs for rows that have a careers link. An unreachable API adds none. */
async function employerEntries(modified: Date): Promise<MetadataRoute.Sitemap> {
  try {
    const ids = await cachedEmployerIds();
    return ids.map((id) => ({
      url: `${SITE_URL}${employerPath(id)}`,
      lastModified: modified,
      changeFrequency: "weekly" as const,
      priority: 0.6,
    }));
  } catch {
    return [];
  }
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
    entry("/opportunities", 0.9, "daily"),
    entry("/data", 0.6, "monthly"),
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
