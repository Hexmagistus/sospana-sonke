import { publicCountries } from "@/lib/countryPageData";
import data from "@/data/countryCareers.json";
import type { CareersCat } from "@/components/CareersDirectory";

// Static per-country employer lists for /job-alerts, built at deploy time from the bundled directory
// snapshot (no DB/backend needed).
const CAREERS = data as Record<string, { name: string; categories: CareersCat[] }>;
export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return publicCountries().map((row) => ({ slug: row.slug }));
}

export async function GET(_req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const cats = CAREERS[slug]?.categories ?? [];
  const seen = new Set<string>();
  const items = cats.flatMap((c) => c.items).filter((it) => (seen.has(it.u) ? false : (seen.add(it.u), true)));
  return Response.json(items.map((it) => ({ a: it.a, n: it.n, u: it.u })));
}
