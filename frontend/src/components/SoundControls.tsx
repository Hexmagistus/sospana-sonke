"use client";

import { useEffect, useId, useSyncExternalStore } from "react";
import {
  getSoundServerSnapshot,
  getSoundSnapshot,
  hydrateSoundChoices,
  subscribeSound,
  toggleMusic,
  toggleSounds,
} from "@/lib/ambientPlayer";

/** Header controls. Music and Sounds are words, off until the reader turns them on. */
export function SoundControls() {
  const snap = useSyncExternalStore(subscribeSound, getSoundSnapshot, getSoundServerSnapshot);
  const noteId = useId();
  useEffect(() => {
    hydrateSoundChoices();
  }, []);

  const musicLabel = snap.musicPlaying ? "Music on" : "Music off";
  const soundsLabel = snap.soundsOn ? "Sounds on" : "Sounds off";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        className={`ss-sound-toggle${snap.musicSaved && !snap.musicPlaying ? " ss-sound-toggle--saved" : ""}`}
        aria-pressed={snap.musicPlaying}
        aria-label={musicLabel}
        aria-describedby={snap.dataSaver ? noteId : undefined}
        disabled={snap.dataSaver}
        onClick={toggleMusic}
      >
        Music
      </button>
      <button
        type="button"
        className="ss-sound-toggle"
        aria-pressed={snap.soundsOn}
        aria-label={soundsLabel}
        onClick={toggleSounds}
      >
        Sounds
      </button>
      {snap.dataSaver ? (
        <p id={noteId} className="text-xs text-ss-muted">
          Music stays off while Data Saver is on.
        </p>
      ) : null}
      {snap.musicSaved && !snap.musicPlaying && !snap.dataSaver ? (
        <p className="sr-only">Your last visit left the soundtrack on. Press Music to play it. It does not start by itself.</p>
      ) : null}
    </div>
  );
}
