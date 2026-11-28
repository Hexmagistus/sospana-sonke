"use client";

import Link from "next/link";
import { useState } from "react";
import {
  bandcampEmbedSrc,
  bandcampPageUrl,
  DEFAULT_GASTRIC_RELEASE_ID,
  formatReleaseDate,
  gastricReleaseById,
  gastricReleasesNewestFirst,
  releaseKindLabel,
} from "@/lib/gastricReleases";

const RELEASES = gastricReleasesNewestFirst();

/** Compact header player. The full track list lives on /music. */
const PLAYER_HEIGHT = 132;

/**
 * The iframe stays in this element. Closing only parks it off-screen, so a
 * track that is already playing can continue across client-side navigations.
 * Bandcamp may still pause media it decides is not visible.
 */
export function MusicDockPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [releaseId, setReleaseId] = useState(DEFAULT_GASTRIC_RELEASE_ID);
  const release = gastricReleaseById(releaseId);
  const listenUrl = bandcampPageUrl(release);

  return (
    <section
      id="ss-music-player"
      aria-label="GASTRIC music player"
      inert={open ? undefined : true}
      className="max-h-[calc(100dvh-17rem)] max-w-md overflow-y-auto overscroll-contain rounded-xl border border-[#FCC033] bg-[#FFF8EC] p-3 text-[#1F2328] md:max-h-none"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#7A5200]">GASTRIC</p>
        <button
          type="button"
          onClick={onClose}
          className="rounded-full px-2 py-1 text-sm font-semibold text-[#1F2328] hover:bg-[#FCF5E5] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#067589]"
        >
          Close
        </button>
      </div>
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
      <p className="mt-2 text-sm">
        <a href={listenUrl} target="_blank" rel="noopener noreferrer" className="font-semibold text-[#05606F] underline">
          Listen on Bandcamp
        </a>
      </p>
      <p className="mt-1 text-xs leading-relaxed text-[#3f4a5c]">
        Press play to start. If it asks for cookies, Listen on Bandcamp opens this release.
      </p>
      <iframe
        src={bandcampEmbedSrc(release)}
        title={`${release.title} by GASTRIC on Bandcamp`}
        className="mt-2 w-full rounded-lg border border-[#1F2328]/10 bg-white"
        style={{ height: PLAYER_HEIGHT }}
        referrerPolicy="strict-origin-when-cross-origin"
      />
      <p className="mt-2 text-sm font-semibold">
        <Link href="/music" className="text-[#05606F] underline">
          All releases
        </Link>
      </p>
    </section>
  );
}
