import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/admin-guard";
import { movieBySlug } from "@/lib/catalog";
import { mergeCatalog, saveMovie, saveReview } from "@/lib/store";
import type { AgeSuitability, Movie, ReviewStatus } from "@/lib/types";
import { validateMovieDraft } from "@/lib/validation";

export async function PATCH(request: Request, context: { params: Promise<{ slug: string }> }) {
  const denied = await requireAdmin();
  if (denied) return denied;
  const { slug } = await context.params;
  const current = movieBySlug(mergeCatalog().movies, slug);
  if (!current) return NextResponse.json({ error: `No title with slug ${slug}.` }, { status: 404 });
  let body: Partial<Movie> & { playbackUrl?: string; licenceEvidenceUrl?: string; reviewStatus?: ReviewStatus; ageSuitability?: AgeSuitability; reviewNotes?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "The edit body was not valid JSON." }, { status: 400 });
  }
  const checked = validateMovieDraft({
    title: body.title ?? current.title,
    description: body.description ?? current.description,
    releaseYear: body.releaseYear ?? current.releaseYear,
    country: body.country ?? current.country,
    ageRating: body.ageRating ?? current.ageRating,
    contentType: body.contentType ?? current.contentType,
    playbackUrl: body.playbackUrl,
    licenceEvidenceUrl: body.licenceEvidenceUrl,
    rightsVerified: Boolean(body.playbackUrl),
  });
  if (!checked.ok) return NextResponse.json({ errors: checked.errors }, { status: 400 });
  const next: Movie = {
    ...current,
    title: body.title?.trim() || current.title,
    description: body.description?.trim() || current.description,
    country: body.country?.trim() || current.country,
    ageRating: body.ageRating ?? current.ageRating,
    featured: body.featured ?? current.featured,
    published: body.published ?? current.published,
    updatedAt: new Date().toISOString(),
  };
  if (body.reviewStatus && body.ageSuitability && body.reviewNotes) {
    next.review = {
      id: current.review?.id ?? next.id,
      movieId: next.id,
      reviewStatus: body.reviewStatus,
      ageSuitability: body.ageSuitability,
      reviewNotes: body.reviewNotes,
      reviewedAt: new Date().toISOString().slice(0, 10),
    };
    saveReview(next.slug, next.review);
  }
  if (body.playbackUrl && body.licenceEvidenceUrl) {
    next.sources = [
      ...current.sources,
      {
        id: `${next.id}-added`,
        movieId: next.id,
        providerId: current.sources[0]?.providerId ?? "manual",
        providerSlug: "manual",
        playbackType: body.playbackUrl.includes(".m3u8") ? "hls" : body.playbackUrl.includes("/embed/") ? "embed" : "mp4",
        url: body.playbackUrl,
        licenceType: "manual",
        licenceEvidenceUrl: body.licenceEvidenceUrl,
        sourceRecordUrl: body.licenceEvidenceUrl,
        licenceTerritories: ["WORLD"],
        licenceExpiry: null,
        rightsVerified: true,
        playbackStatus: "available",
        lastVerifiedAt: new Date().toISOString().slice(0, 10),
        rightsHolder: "Entered by an admin",
        rightsHolderSource: "manual",
        subtitles: [],
        qualityNote: "Added from the admin dashboard after a licence URL was supplied.",
      },
    ];
  }
  saveMovie(next);
  try {
    const remote = await pushMovie(next);
    return NextResponse.json({ movie: next, detail: remote });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: message, detail: "The demonstration file was updated. Supabase was not." },
      { status: 502 },
    );
  }
}

async function pushMovie(movie: Movie): Promise<string> {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return "Saved in data/runtime-state.json. SUPABASE_SERVICE_ROLE_KEY is not set, so Supabase was not updated.";
  }
  const response = await fetch(`${url.replace(/\/$/, "")}/rest/v1/movies?slug=eq.${encodeURIComponent(movie.slug)}`, {
    method: "PATCH",
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "content-type": "application/json",
      prefer: "return=minimal",
    },
    body: JSON.stringify({
      title: movie.title,
      description: movie.description,
      country: movie.country,
      age_rating: movie.ageRating,
      featured: movie.featured,
      published: movie.published,
    }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Supabase rejected the movie update (HTTP ${response.status}): ${text.slice(0, 400)}`);
  }
  return "Updated the movie row in Supabase and the local demonstration store.";
}
