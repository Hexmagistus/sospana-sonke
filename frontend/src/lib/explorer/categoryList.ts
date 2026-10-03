/** The company-name list shown over the map for the chosen country and category.

Each entry is "Name (14)" or "Name (NCY)". The number is the vacancy count we hold
for that employer, a real zero included ("(0)"). NCY means Not counted yet: no count
is known, which is not the same as no vacancies (see notCounted.ts). Alphabetical,
nothing hidden or paged. */

import { hasCountedResult } from "../notCounted";
import type { Company } from "../types";

export const NCY = "NCY";

export type CategoryListItem = {
  id: string;
  name: string;
  /** Careers page, or null when we do not have one. */
  url: string | null;
  /** "14", "0" or "NCY". */
  value: string;
  counted: boolean;
  /** "Atlassian (14)" / "Canva (NCY)". */
  text: string;
};

export function vacancyValue(company: Pick<Company, "open_vacancies" | "open_vacancies_known">): string {
  return hasCountedResult(company) ? String(company.open_vacancies ?? 0) : NCY;
}

export function categoryListItems(
  companies: ReadonlyArray<Pick<Company, "id" | "company_name" | "careers_url" | "open_vacancies" | "open_vacancies_known">>,
): CategoryListItem[] {
  return companies
    .map((c) => {
      const value = vacancyValue(c);
      return {
        id: c.id,
        name: c.company_name,
        url: c.careers_url || null,
        value,
        counted: value !== NCY,
        text: `${c.company_name} (${value})`,
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name, "en") || a.id.localeCompare(b.id));
}

/** Two columns for the map overlay: the first half left, the rest right. Short lists stay in one. */
export function splitColumns<T>(items: readonly T[], minForTwo = 8): [T[], T[]] {
  if (items.length < minForTwo) return [items.slice(), []];
  const half = Math.ceil(items.length / 2);
  return [items.slice(0, half), items.slice(half)];
}
