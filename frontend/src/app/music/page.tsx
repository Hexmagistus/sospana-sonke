import type { Metadata } from "next";
import {
  bandcampEmbedHeight,
  bandcampEmbedSrc,
  bandcampPageUrl,
  formatReleaseDate,
  GASTRIC_ARTIST,
  GASTRIC_BAND_URL,
  gastricReleasesNewestFirst,
  releaseKindLabel,
} from "@/lib/gastricReleases";

export const metadata: Metadata = {
  title: "Music",
  description:
    "GASTRIC's albums and the single COLONIZERS ARE COMING BACK, newest first, in Bandcamp's player. Includes INITIATES OF THE FLAME.",
  alternates: { canonical: "/music" },
  openGraph: {
    title: "GASTRIC music",
    description:
      "Listen to GASTRIC on Bandcamp's player. Albums and one single, newest first.",
    url: "/music",
  },
};

export default function MusicPage() {
  const releases = gastricReleasesNewestFirst();

  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <header className="space-y-2">
        <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#7A5200]">{GASTRIC_ARTIST}</p>
        <h1 className="text-3xl font-bold text-[#1F2328]">Music</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-[#3f4a5c]">
          Albums and one single by {GASTRIC_ARTIST}, newest first. Each player is Bandcamp&apos;s own,
          so the audio stays on Bandcamp. Press play when you want sound. If a player says cookies
          are disabled, Listen on Bandcamp still opens that release. The Music control under the
          header can keep one release going while you look around the rest of the site.
        </p>
        <p>
          <a
            href={GASTRIC_BAND_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-[#05606F] underline"
          >
            GASTRIC on Bandcamp
          </a>
        </p>
      </header>

      <ol className="space-y-5">
        {releases.map((release, index) => (
          <li key={release.id} className="ss-card">
            <div className="flex gap-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={release.artwork}
                alt={`${release.title} cover`}
                width={210}
                height={210}
                className="h-24 w-24 shrink-0 rounded-xl object-cover ring-1 ring-[#FCC033]"
              />
              <div className="min-w-0">
                <h2 className="text-xl font-bold text-[#1F2328]">{release.title}</h2>
                <p className="mt-1 text-sm text-[#3f4a5c]">
                  {GASTRIC_ARTIST} · {releaseKindLabel(release.kind)} · {formatReleaseDate(release.releasedOn)}
                </p>
                <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                  <a
                    href={bandcampPageUrl(release)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-[#05606F] underline"
                  >
                    Listen on Bandcamp
                  </a>
                  <a
                    href={bandcampPageUrl(release)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-[#05606F] underline"
                  >
                    Buy or support on Bandcamp
                  </a>
                </p>
              </div>
            </div>
            <iframe
              src={bandcampEmbedSrc(release)}
              title={`${release.title} by GASTRIC on Bandcamp`}
              className="mt-4 w-full rounded-xl border border-[#1F2328]/10 bg-white"
              style={{ height: bandcampEmbedHeight(release.tracks.length) }}
              loading={index === 0 ? "eager" : "lazy"}
              referrerPolicy="strict-origin-when-cross-origin"
            />
            <ol className="mt-3 list-decimal space-y-0.5 pl-5 text-sm text-[#3f4a5c]">
              {release.tracks.map((track) => (
                <li key={track}>{track}</li>
              ))}
            </ol>
          </li>
        ))}
      </ol>
    </article>
  );
}
