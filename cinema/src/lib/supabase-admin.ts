import "server-only";

import type { Movie, Review, Takedown, TakedownStatus } from "./types";

// Server-only Supabase writes. The service role key never reaches the browser.

function base(): string | null {
  const url = process.env.SUPABASE_URL;
  return url ? url.replace(/\/$/, "") : null;
}

export function supabaseUrlSet(): boolean {
  return Boolean(base());
}

export function serviceKeySet(): boolean {
  return Boolean(base() && process.env.SUPABASE_SERVICE_ROLE_KEY);
}

function headers(key: string, prefer?: string): Record<string, string> {
  const out: Record<string, string> = {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "content-type": "application/json",
  };
  if (prefer) out.prefer = prefer;
  return out;
}

async function failure(response: Response, what: string): Promise<Error> {
  const text = await response.text();
  return new Error(`Supabase rejected the ${what} (HTTP ${response.status}): ${text.slice(0, 400)}`);
}

/**
 * Store a complaint. Uses the service role key when it is set. Otherwise it
 * uses the anon key, which migration 0002 allows to insert the four form
 * columns only (it cannot read complaints back).
 */
export async function insertTakedownRemote(takedown: Pick<Takedown, "claimantName" | "contactEmail" | "contentId" | "reason">): Promise<"service" | "anon"> {
  const url = base();
  const service = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const anon = process.env.SUPABASE_ANON_KEY;
  const key = service || anon;
  if (!url || !key) throw new Error("SUPABASE_URL and a Supabase key are not set.");
  const response = await fetch(`${url}/rest/v1/takedown_requests`, {
    method: "POST",
    headers: headers(key, "return=minimal"),
    body: JSON.stringify({
      claimant_name: takedown.claimantName,
      contact_email: takedown.contactEmail,
      content_id: takedown.contentId,
      reason: takedown.reason,
    }),
    cache: "no-store",
  });
  if (!response.ok) throw await failure(response, "complaint");
  return service ? "service" : "anon";
}

type TakedownRow = {
  id: string;
  claimant_name: string;
  contact_email: string;
  content_id: string;
  reason: string;
  status: TakedownStatus;
  created_at: string;
};

export async function listTakedownsRemote(): Promise<Takedown[]> {
  const url = base();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_SERVICE_ROLE_KEY is not set, so complaints stored in Supabase cannot be listed.");
  const response = await fetch(`${url}/rest/v1/takedown_requests?select=*&order=created_at.desc&limit=200`, {
    headers: headers(key),
    cache: "no-store",
  });
  if (!response.ok) throw await failure(response, "complaint list request");
  const rows = (await response.json()) as TakedownRow[];
  return rows.map((row) => ({
    id: row.id,
    claimantName: row.claimant_name,
    contactEmail: row.contact_email,
    contentId: row.content_id,
    reason: row.reason,
    status: row.status,
    createdAt: row.created_at,
  }));
}

export async function pushMovieRemote(movie: Movie): Promise<void> {
  const url = base();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_SERVICE_ROLE_KEY is not set, so Supabase cannot be updated.");
  const response = await fetch(`${url}/rest/v1/movies?slug=eq.${encodeURIComponent(movie.slug)}`, {
    method: "PATCH",
    headers: headers(key, "return=representation"),
    body: JSON.stringify({
      title: movie.title,
      description: movie.description,
      country: movie.country,
      age_rating: movie.ageRating,
      featured: movie.featured,
      published: movie.published,
      updated_at: movie.updatedAt,
    }),
    cache: "no-store",
  });
  if (!response.ok) throw await failure(response, "movie update");
  const rows = (await response.json()) as unknown[];
  if (rows.length === 0) throw new Error(`Supabase has no movie row with slug ${movie.slug}.`);
}

export async function pushReviewRemote(movieId: string, review: Review): Promise<void> {
  const url = base();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_SERVICE_ROLE_KEY is not set, so Supabase cannot be updated.");
  const body = {
    review_status: review.reviewStatus,
    age_suitability: review.ageSuitability,
    review_notes: review.reviewNotes,
    reviewed_at: review.reviewedAt,
  };
  const patch = await fetch(`${url}/rest/v1/content_reviews?movie_id=eq.${encodeURIComponent(movieId)}`, {
    method: "PATCH",
    headers: headers(key, "return=representation"),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!patch.ok) throw await failure(patch, "review update");
  const rows = (await patch.json()) as unknown[];
  if (rows.length > 0) return;
  const insert = await fetch(`${url}/rest/v1/content_reviews`, {
    method: "POST",
    headers: headers(key, "return=minimal"),
    body: JSON.stringify({ movie_id: movieId, ...body }),
    cache: "no-store",
  });
  if (!insert.ok) throw await failure(insert, "review insert");
}
