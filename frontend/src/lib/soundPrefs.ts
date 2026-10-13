/** Local soundtrack and UI-sound choices. "on" is the only stored yes. */

export const MUSIC_KEY = "ss-music";
export const SOUNDS_KEY = "ss-sounds";
export const AMBIENT_SRC = "/audio/ambient.ogg";

type KeyValue = {
  getItem(key: string): string | null;
  setItem?(key: string, value: string): void;
};

export function readChoice(storage: KeyValue | null, key: string): boolean {
  if (!storage) return false;
  try {
    return storage.getItem(key) === "on";
  } catch {
    return false;
  }
}

export function writeChoice(storage: KeyValue | null, key: string, on: boolean): void {
  if (!storage || !storage.setItem) return;
  try {
    storage.setItem(key, on ? "on" : "off");
  } catch {
    // Private mode can refuse the write. Playback for this visit still works.
  }
}

/** A click while the loop is silent starts it. A click while it plays stops it. */
export function musicClickAction(playing: boolean): "play" | "stop" {
  return playing ? "stop" : "play";
}

/** UI clicks stay quiet unless the reader turned sounds on and did not ask for less motion. */
export function uiSoundAllowed(soundsOn: boolean, reducedMotion: boolean): boolean {
  return soundsOn && !reducedMotion;
}

/** Data Saver must not fetch the soundtrack file. */
export function mayLoadAmbient(saveData: boolean): boolean {
  return !saveData;
}

/** Hidden tabs pause. Coming back resumes only if this visit had already started the loop. */
export function shouldPlayAmbient(playing: boolean, hidden: boolean, saveData: boolean): boolean {
  return playing && !hidden && !saveData;
}
