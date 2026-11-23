import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/admin-guard";
import { movieBySlug } from "@/lib/catalog";
import { getPublicCatalog } from "@/lib/public-catalog";
import { saveMovie, saveReview } from "@/lib/store";
import { pushMovieRemote, pushReviewRemote, serviceKeySet, supabaseUrlSet } from "@/lib/supabase-admin";
import type { AgeSuitability, Movie, ReviewStatus } from "@/lib/types";
import { validateMovieDraft } from "@/lib/validation";

export async function PATCH(request: Request, context: { params: Promise<{ slug: string }> }) {
  const denied = await requireAdmin();
  if (denied) return denied;
  const { slug } = await context.params;
  const remote = supabaseUrlSet();
  if (remote && !serviceKeySet()) {
    return NextResponse.json(
      { error: "This site reads from Supabase, but SUPABASE_SERVICE_ROLE_KEY is not set, so admin edits cannot be saved." },
      { status: 503 },
    );
  }
  const current = movieBySlug((await getPublicCatalog()).movies, slug);
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
  if (remote) {
    if (body.playbackUrl && body.licenceEvidenceUrl) {
      return NextResponse.json(
        { error: "Adding a playback source from the dashboard is not wired to Supabase yet. Add the streaming_sources row in Supabase with its licence evidence." },
        { status: 501 },
      );
    }
    try {
      await pushMovieRemote(next);
      if (next.review && next.review !== current.review) await pushReviewRemote(next.id, next.review);
      return NextResponse.json({ movie: next, detail: "Saved in Supabase." });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return NextResponse.json({ error: message }, { status: 502 });
    }
  }
  try {
    if (next.review && next.review !== current.review) saveReview(next.slug, next.review);
    saveMovie(next);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `The edit could not be saved on this server: ${message}. Configure Supabase to save admin edits.` },
      { status: 503 },
    );
  }
  return NextResponse.json({ movie: next, detail: "Saved in data/runtime-state.json. Supabase is not configured." });
}
