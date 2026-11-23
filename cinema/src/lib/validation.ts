import type { AgeRating, ContentType, Movie, TakedownStatus } from "./types";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const AGES: AgeRating[] = ["All", "6+", "9+", "13+", "16+", "18+"];
const TYPES: ContentType[] = ["movie", "short", "series", "documentary"];

export type FieldErrors = Record<string, string>;

export function validateTakedown(input: {
  claimantName?: string;
  contactEmail?: string;
  contentId?: string;
  reason?: string;
  knownIds?: string[];
}): { ok: true; value: { claimantName: string; contactEmail: string; contentId: string; reason: string } } | { ok: false; errors: FieldErrors } {
  const errors: FieldErrors = {};
  const claimantName = (input.claimantName ?? "").trim();
  const contactEmail = (input.contactEmail ?? "").trim();
  const contentId = (input.contentId ?? "").trim();
  const reason = (input.reason ?? "").trim();
  if (claimantName.length < 2 || claimantName.length > 120) errors.claimantName = "Enter the claimant's name (2–120 characters).";
  if (!EMAIL.test(contactEmail) || contactEmail.length > 200) errors.contactEmail = "Enter a real email address so the complaint can be answered.";
  if (!contentId) errors.contentId = "Choose the title this complaint is about.";
  if (input.knownIds && !input.knownIds.includes(contentId)) errors.contentId = "That title is not in the catalogue.";
  if (reason.length < 20 || reason.length > 5000) errors.reason = "Describe the rights problem in at least 20 characters.";
  if (Object.keys(errors).length) return { ok: false, errors };
  return { ok: true, value: { claimantName, contactEmail, contentId, reason } };
}

export function validateMovieDraft(input: {
  title?: string;
  description?: string;
  releaseYear?: number;
  country?: string;
  ageRating?: string;
  contentType?: string;
  playbackUrl?: string;
  licenceEvidenceUrl?: string;
  rightsVerified?: boolean;
}): { ok: true } | { ok: false; errors: FieldErrors } {
  const errors: FieldErrors = {};
  const title = (input.title ?? "").trim();
  const description = (input.description ?? "").trim();
  if (title.length < 1 || title.length > 300) errors.title = "A title is required.";
  if (description.length < 20) errors.description = "Add a description of at least 20 characters.";
  if (!input.releaseYear || input.releaseYear < 1888 || input.releaseYear > 2100) errors.releaseYear = "Enter the release year.";
  if (!(input.country ?? "").trim()) errors.country = "Enter the country.";
  if (!AGES.includes(input.ageRating as AgeRating)) errors.ageRating = "Choose an age rating.";
  if (!TYPES.includes(input.contentType as ContentType)) errors.contentType = "Choose a content type.";
  const playback = (input.playbackUrl ?? "").trim();
  const evidence = (input.licenceEvidenceUrl ?? "").trim();
  if (playback || input.rightsVerified) {
    if (!playback.startsWith("https://")) errors.playbackUrl = "Authorized playback must be an https URL, or leave it empty.";
    if (!evidence.startsWith("http://") && !evidence.startsWith("https://")) {
      errors.licenceEvidenceUrl = "A rights-verified title needs the licence evidence URL.";
    }
    if (!input.rightsVerified) errors.rightsVerified = "Confirm that the licence was checked before playback can be saved.";
  }
  if (Object.keys(errors).length) return { ok: false, errors };
  return { ok: true };
}

export function slugify(title: string): string {
  const slug = title
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return slug || "title";
}

export function applyMoviePatch(movie: Movie, patch: Partial<Movie> & { playbackUrl?: string; licenceEvidenceUrl?: string }): Movie {
  return {
    ...movie,
    ...patch,
    title: patch.title?.trim() || movie.title,
    description: patch.description?.trim() || movie.description,
    updatedAt: new Date().toISOString(),
  };
}

export function isTakedownStatus(value: string): value is TakedownStatus {
  return value === "received" || value === "reviewing" || value === "removed" || value === "rejected";
}
