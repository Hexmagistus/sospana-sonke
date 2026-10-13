/** Public landing slugs. A page is only linked when the live index has rows for it. */

export const PROGRAMME_PAGES = [
  { slug: "learnerships", type: "learnership", label: "Learnerships" },
  { slug: "internships", type: "internship", label: "Internships" },
  { slug: "bursaries", type: "bursary", label: "Bursaries" },
  { slug: "graduate-programmes", type: "graduate_programme", label: "Graduate programmes" },
] as const;

export type ProgrammePage = (typeof PROGRAMME_PAGES)[number];

export function programmeFromSlug(slug: string): ProgrammePage | null {
  return PROGRAMME_PAGES.find((row) => row.slug === slug) ?? null;
}

export function facetSlug(name: string): string {
  const folded = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  return folded.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "category";
}
