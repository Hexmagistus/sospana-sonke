import "server-only";

import type { Movie, Review, StreamSource } from "./types";

type RemoteRow = {
  id: string;
  title: string;
  slug: string;
  description: string;
  release_year: number;
  runtime_seconds: number;
  genres: string[];
  language: string;
  country: string;
  director: string;
  cast_members: string[];
  content_type: Movie["contentType"];
  age_rating: Movie["ageRating"];
  poster_url: string | null;
  backdrop_url: string | null;
  trailer_url: string | null;
  featured: boolean;
  catalogue_note: string | null;
  created_at: string;
  updated_at: string;
  sources: StreamSource[] | null;
  review: Review | null;
  category_slugs: string[] | null;
};

export function supabaseConfigured(): boolean {
  return Boolean(process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY);
}

export function mapRemoteMovie(row: RemoteRow): Movie {
  return {
    id: row.id,
    slug: row.slug,
    title: row.title,
    description: row.description,
    releaseYear: row.release_year,
    runtimeSeconds: row.runtime_seconds,
    genres: row.genres ?? [],
    language: row.language,
    country: row.country,
    director: row.director,
    cast: row.cast_members ?? [],
    contentType: row.content_type,
    ageRating: row.age_rating,
    posterUrl: row.poster_url,
    backdropUrl: row.backdrop_url,
    trailerUrl: row.trailer_url,
    categorySlugs: row.category_slugs ?? [],
    featured: row.featured,
    published: true,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    note: row.catalogue_note,
    sources: (row.sources ?? []).map((source) => ({
      ...source,
      providerSlug: source.providerSlug || "supabase",
      rightsHolderSource: source.rightsHolderSource || "supabase",
      subtitles: source.subtitles ?? [],
      qualityNote: source.qualityNote ?? "",
    })),
    review: row.review,
  };
}

export async function fetchSupabaseMovies(): Promise<Movie[]> {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error("SUPABASE_URL and SUPABASE_ANON_KEY are not set.");
  }
  const endpoint = `${url.replace(/\/$/, "")}/rest/v1/public_catalog?select=*`;
  const response = await fetch(endpoint, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
    cache: "no-store",
  });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(`Supabase public_catalog answered HTTP ${response.status}: ${body.slice(0, 400)}`);
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    throw new Error("Supabase public_catalog did not return JSON.");
  }
  if (!Array.isArray(parsed)) {
    throw new Error("Supabase public_catalog did not return a list.");
  }
  return (parsed as RemoteRow[]).map(mapRemoteMovie);
}
