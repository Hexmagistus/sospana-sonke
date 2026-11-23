export type AgeRating = "All" | "6+" | "9+" | "13+" | "16+" | "18+";
export type ContentType = "movie" | "short" | "series" | "documentary";
export type PlaybackType = "embed" | "mp4" | "hls";
export type ReviewStatus = "pending" | "approved" | "rejected";
export type AgeSuitability = "preschool" | "6-8" | "9-12" | "family" | "not-for-kids";

export type Subtitle = {
  language: string;
  label: string;
  url: string;
};

export type StreamSource = {
  id: string;
  movieId: string;
  providerId: string;
  providerSlug: string;
  playbackType: PlaybackType;
  url: string;
  licenceType: string;
  licenceEvidenceUrl: string;
  sourceRecordUrl: string;
  licenceTerritories: string[];
  licenceExpiry: string | null;
  rightsVerified: boolean;
  playbackStatus: "available" | "unavailable" | "broken";
  lastVerifiedAt: string;
  rightsHolder: string;
  rightsHolderSource: string;
  subtitles: Subtitle[];
  qualityNote: string;
};

export type Review = {
  id: string;
  movieId: string;
  reviewStatus: ReviewStatus;
  ageSuitability: AgeSuitability;
  reviewNotes: string;
  reviewedAt: string;
};

export type Movie = {
  id: string;
  slug: string;
  title: string;
  description: string;
  releaseYear: number;
  runtimeSeconds: number;
  genres: string[];
  language: string;
  country: string;
  director: string;
  cast: string[];
  contentType: ContentType;
  ageRating: AgeRating;
  posterUrl: string | null;
  backdropUrl: string | null;
  trailerUrl: string | null;
  categorySlugs: string[];
  featured: boolean;
  published: boolean;
  createdAt: string;
  updatedAt: string;
  note: string | null;
  sources: StreamSource[];
  review: Review | null;
};

export type Category = {
  id: string;
  slug: string;
  name: string;
  description: string;
};

export type ContentProvider = {
  id: string;
  slug: string;
  providerName: string;
  websiteUrl: string;
  providerType: string;
  apiStatus: string;
  termsReference: string;
};

export type CatalogFile = {
  demo: boolean;
  verifiedOn: string;
  name: string;
  tagline: string;
  heroSlug: string;
  trending: string[];
  popular: string[];
  categories: Category[];
  sources: ContentProvider[];
  movies: Movie[];
};

export type TakedownStatus = "received" | "reviewing" | "removed" | "rejected";

export type Takedown = {
  id: string;
  claimantName: string;
  contactEmail: string;
  contentId: string;
  reason: string;
  status: TakedownStatus;
  createdAt: string;
};
