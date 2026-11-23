import "server-only";

import { seedCatalog } from "./catalog";
import { mergeCatalog, readOverlay } from "./store";
import { fetchSupabaseMovies, supabaseConfigured } from "./supabase";
import type { CatalogFile } from "./types";

export type PublicCatalog = CatalogFile & {
  origin: "demonstration" | "supabase";
  warning: string | null;
};

export async function getPublicCatalog(): Promise<PublicCatalog> {
  const seed = seedCatalog();
  const merged = mergeCatalog(seed, readOverlay());
  if (!supabaseConfigured()) {
    return { ...merged, origin: "demonstration", warning: null };
  }
  try {
    const movies = await fetchSupabaseMovies();
    if (movies.length === 0) {
      return {
        ...merged,
        origin: "demonstration",
        warning: "Supabase returned no published titles. The demonstration catalogue is showing.",
      };
    }
    return { ...seed, movies, demo: false, origin: "supabase", warning: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      ...merged,
      origin: "demonstration",
      warning: `${message} The demonstration catalogue is showing.`,
    };
  }
}
