"use client";

import Link from "next/link";
import { useState } from "react";
import {
  bandcampEmbedHeight,
  bandcampEmbedSrc,
  bandcampPageUrl,
  DEFAULT_GASTRIC_RELEASE_ID,
  formatReleaseDate,
  gastricReleaseById,
  gastricReleasesNewestFirst,
  releaseKindLabel,
} from "@/lib/gastricReleases";

const RELEASES = gastricReleasesNewestFirst();

/**
 * The iframe stays in this element. Collapsing only parks it off-screen, so a
 * track that is already playing can continue, including across client-side
 * navigations. Bandcamp may still pause media it decides is not visible.
 */
export function MusicDockPanel({ open }: { open: boolean }) {
  const [releaseId, setReleaseId] = useState(DEFAULT_GASTRIC_RELEASE_ID);
  const release = gastricReleaseById(releaseId);

  return (
    <section
      id="ss-music-player"
      aria-label="GASTRIC music player"
      inert={open ? undefined : true}
      className={
        open
          ? "pointer-events-auto max-h-[min(28rem,calc(100dvh-16.5rem-env(safe-area-inset-bottom)))] w-[min(22rem,calc(100vw-1.5rem))] overflow-y-auto overscroll-contain rounded-2xl border-2 border-[#FCC033] bg-[#FFF8EC] p-3 text-[#1F2328] shadow-[0_18px_40px_-18px_rgba(31,35,40,0.45)]"
          : "pointer-events-none fixed left-[-12000px] top-0 h-[28rem] w-[22rem] overflow-hidden"
      }
    >
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#7A5200]">GASTRIC</p>
      <label htmlFor="ss-music-release" className="mt-2 block text-sm font-semibold">
        Choose a release
        <select
          id="ss-music-release"
          className="mt-1 w-full rounded-lg border border-[#1F2328]/20 bg-white px-2 py-2 text-sm font-medium text-[#1F2328] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#067589]"
          value={release.id}
          onChange={(event) => setReleaseId(Number(event.target.value))}
        >
          {RELEASES.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>
      </label>
      <p className="mt-2 text-xs text-[#3f4a5c]">
        {releaseKindLabel(release.kind)} · {formatReleaseDate(release.releasedOn)}
      </p>
      <iframe
        src={bandcampEmbedSrc(release)}
        title={`${release.title} by GASTRIC on Bandcamp`}
        className="mt-2 w-full rounded-lg border border-[#1F2328]/10 bg-white"
        style={{ height: bandcampEmbedHeight(release.tracks.length) }}
        referrerPolicy="strict-origin-when-cross-origin"
      />
      <p className="mt-2 text-xs leading-relaxed text-[#3f4a5c]">
        Playback starts when you press play. Audio is streamed by Bandcamp.
      </p>
      <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm font-semibold">
        <a
          href={bandcampPageUrl(release)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#05606F] underline"
        >
          Buy or support on Bandcamp
        </a>
        <Link href="/music" className="text-[#05606F] underline">
          All releases
        </Link>
      </p>
    </section>
  );
}
