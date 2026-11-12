// GASTRIC (gastricl.bandcamp.com) discography, newest first.
// Ids are the item_id values from each release page's bc-page-properties
// meta tag, checked on 12 November 2026 against the official EmbeddedPlayer
// document, which listed these same titles and tracks. Audio stays on Bandcamp.

export type GastricKind = "album" | "track";

export type GastricRelease = {
  id: number;
  kind: GastricKind;
  title: string;
  /** Path on gastricl.bandcamp.com, including the leading slash. */
  path: string;
  artwork: string;
  /** Calendar day the release page published, UTC. */
  releasedOn: string;
  tracks: readonly string[];
};

export const GASTRIC_ARTIST = "GASTRIC";
export const GASTRIC_BAND_URL = "https://gastricl.bandcamp.com";

/** INITIATES OF THE FLAME. The floating player opens on this release. */
export const DEFAULT_GASTRIC_RELEASE_ID = 744084806;

export const GASTRIC_RELEASES: readonly GastricRelease[] = [
  {
    id: 3499065470,
    kind: "track",
    title: "COLONIZERS ARE COMING BACK",
    path: "/track/colonizers-are-coming-back",
    artwork: "https://f4.bcbits.com/img/a1414201605_16.jpg",
    releasedOn: "2025-11-19",
    tracks: ["COLONIZERS ARE COMING BACK"],
  },
  {
    id: 3713535762,
    kind: "album",
    title: "MAN AND MEMORY",
    path: "/album/man-and-memory",
    artwork: "https://f4.bcbits.com/img/a0225125200_16.jpg",
    releasedOn: "2025-07-25",
    tracks: [
      "Back o the Curve _",
      "Consequence is Harmony",
      "Curious Blacks",
      "He who can be SILENT",
      "Memory will Judge",
      "The hidden Goddess",
      "Akhenaten",
    ],
  },
  {
    id: 3347381230,
    kind: "album",
    title: "ELI DNA 2",
    path: "/album/eli-dna-2",
    artwork: "https://f4.bcbits.com/img/a1794352349_16.jpg",
    releasedOn: "2025-06-02",
    tracks: [
      "Invisible College",
      "Sevenfold Path",
      "Hidden Sun",
      "Rite of Perfection",
      "Fountain-Waters of Light",
      "Ninth Gate",
      "The Magus Code",
      "Celestial Essence",
    ],
  },
  {
    id: 594928023,
    kind: "album",
    title: "LODEWYKXS",
    path: "/album/lodewykxs",
    artwork: "https://f4.bcbits.com/img/a2808447154_16.jpg",
    releasedOn: "2025-03-25",
    tracks: ["GODZILLA ON3", "GODZILLA AA", "GODZILLA 2", "GODZILLA B", "GODZILLA C", "GODZILLA 3"],
  },
  {
    id: 3481409865,
    kind: "album",
    title: "SANCTUM SANCTORUM",
    path: "/album/sanctum-sanctorum",
    artwork: "https://f4.bcbits.com/img/a2836888293_16.jpg",
    releasedOn: "2024-12-10",
    tracks: [
      "THE VEIL CONSORTS",
      "DEA_TH NOTES",
      "FILE EXTENSIONS",
      "IRONCLADS",
      "LOGOS",
      "INNER PORTAL",
      "CONSECRATION",
      "3rd PORTAL",
      "JACOB'S LADDER",
    ],
  },
  {
    id: 1529620876,
    kind: "album",
    title: "uCansi",
    path: "/album/ucansi",
    artwork: "https://f4.bcbits.com/img/a0795241272_16.jpg",
    releasedOn: "2024-11-15",
    tracks: [
      "CALM ME DOWN",
      "eVAAL",
      "I GOT FAITH",
      "JOZI",
      "MIND- YOUR BIZ",
      "RABA KHOTHA",
      "SIDELINER",
      "SNCENCEZA",
      "THOKOZANI",
      "YOMASE SHOES",
      "ZERO 16",
      "ZODIAC",
    ],
  },
  {
    id: 686813694,
    kind: "album",
    title: "N.E.O",
    path: "/album/n-e-o",
    artwork: "https://f4.bcbits.com/img/a1691863510_16.jpg",
    releasedOn: "2024-10-06",
    tracks: [
      "VULCAN",
      "LETTERS MAKE MAN",
      "FORMLESS",
      "GREAT GRAN",
      "SHORT NAP",
      "NEO",
      "FORM",
      "REINCARNATION",
      "VITAL BODY",
    ],
  },
  {
    id: 942910523,
    kind: "album",
    title: "ELI DNA",
    path: "/album/eli-dna",
    artwork: "https://f4.bcbits.com/img/a1661565587_16.jpg",
    releasedOn: "2024-09-07",
    tracks: ["ANDILE", "INNER GUARD", "TAROT", "SCARAB", "GRAND SUN", "IMMUNE", "SALT", "TSHABALALA"],
  },
  {
    id: 744084806,
    kind: "album",
    title: "INITIATES OF THE FLAME",
    path: "/album/initiates-of-the-flame",
    artwork: "https://f4.bcbits.com/img/a0749358306_16.jpg",
    releasedOn: "2024-08-22",
    tracks: [
      "ADEPTUS EXEMPTUS",
      "ADEPTUS MAJOR",
      "ADEPTUS MINOR",
      "ARCANA",
      "AMENRA",
      "ASPIRANT",
      "ASTRAL PLANE",
      "BROTHERHOOD OF MAN",
    ],
  },
];

export function gastricReleasesNewestFirst(): GastricRelease[] {
  return [...GASTRIC_RELEASES].sort((a, b) => b.releasedOn.localeCompare(a.releasedOn));
}

export function gastricReleaseById(id: number): GastricRelease {
  const found = GASTRIC_RELEASES.find((release) => release.id === id);
  if (found) return found;
  const fallback = GASTRIC_RELEASES.find((release) => release.id === DEFAULT_GASTRIC_RELEASE_ID);
  if (!fallback) throw new Error("GASTRIC release list is empty");
  return fallback;
}

export function releaseKindLabel(kind: GastricKind): "Single" | "Album" {
  return kind === "track" ? "Single" : "Album";
}

export function bandcampPageUrl(release: Pick<GastricRelease, "path">): string {
  return `${GASTRIC_BAND_URL}${release.path}`;
}

/** Official Bandcamp player. autoplay is omitted so nothing starts by itself. */
export function bandcampEmbedSrc(release: Pick<GastricRelease, "id" | "kind">): string {
  return `https://bandcamp.com/EmbeddedPlayer/${release.kind}=${release.id}/size=large/bgcol=ffffff/linkcol=067589/tracklist=true/artwork=small/transparent=true/`;
}

/** Controls row plus one row per track, matching Bandcamp's large tracklist player. */
export function bandcampEmbedHeight(trackCount: number): number {
  return 148 + Math.max(1, trackCount) * 33;
}

export function formatReleaseDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}
