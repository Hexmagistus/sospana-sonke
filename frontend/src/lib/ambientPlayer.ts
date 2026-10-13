"use client";

import {
  AMBIENT_SRC,
  MUSIC_KEY,
  SOUNDS_KEY,
  mayLoadAmbient,
  musicClickAction,
  readChoice,
  shouldPlayAmbient,
  uiSoundAllowed,
  writeChoice,
} from "@/lib/soundPrefs";

export type SoundSnapshot = {
  musicPlaying: boolean;
  musicSaved: boolean;
  soundsOn: boolean;
  dataSaver: boolean;
};

const serverSnapshot: SoundSnapshot = {
  musicPlaying: false,
  musicSaved: false,
  soundsOn: false,
  dataSaver: false,
};

let snap: SoundSnapshot = serverSnapshot;
const listeners = new Set<() => void>();
let audio: HTMLAudioElement | null = null;
let bound = false;
let hydrated = false;

function emit() {
  listeners.forEach((listener) => listener());
}

function saveDataOn(): boolean {
  if (typeof navigator === "undefined") return false;
  const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
  if (connection?.saveData) return true;
  try {
    if (window.localStorage.getItem("ss-data-saver") === "1") return true;
  } catch {
    // Private mode can refuse the read. The connection flag above still applies.
  }
  if (typeof location !== "undefined" && location.pathname.startsWith("/lite")) return true;
  return false;
}

function bindVisibility() {
  if (bound || typeof document === "undefined") return;
  bound = true;
  document.addEventListener("visibilitychange", () => {
    if (!audio) return;
    if (shouldPlayAmbient(snap.musicPlaying, document.hidden, snap.dataSaver)) {
      void audio.play();
    } else {
      audio.pause();
    }
  });
}

function ensureAmbient(): HTMLAudioElement {
  if (!audio) {
    audio = new Audio();
    audio.preload = "none";
    audio.loop = true;
  }
  if (!audio.getAttribute("src")) audio.src = AMBIENT_SRC;
  return audio;
}

export function subscribeSound(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSoundSnapshot(): SoundSnapshot {
  return snap;
}

export function getSoundServerSnapshot(): SoundSnapshot {
  return serverSnapshot;
}

export function hydrateSoundChoices() {
  if (hydrated || typeof window === "undefined") return;
  hydrated = true;
  bindVisibility();
  const dataSaver = saveDataOn();
  snap = {
    musicPlaying: false,
    musicSaved: dataSaver ? false : readChoice(window.localStorage, MUSIC_KEY),
    soundsOn: readChoice(window.localStorage, SOUNDS_KEY),
    dataSaver,
  };
  emit();
}

export function toggleMusic() {
  bindVisibility();
  const dataSaver = saveDataOn();
  if (!mayLoadAmbient(dataSaver)) {
    if (audio) audio.pause();
    snap = { ...snap, musicPlaying: false, dataSaver: true };
    emit();
    return;
  }
  if (musicClickAction(snap.musicPlaying) === "stop") {
    audio?.pause();
    writeChoice(window.localStorage, MUSIC_KEY, false);
    snap = { ...snap, musicPlaying: false, musicSaved: false, dataSaver: false };
    emit();
    return;
  }
  const element = ensureAmbient();
  writeChoice(window.localStorage, MUSIC_KEY, true);
  snap = { ...snap, musicPlaying: true, musicSaved: true, dataSaver: false };
  emit();
  void element.play().catch(() => {
    snap = { ...snap, musicPlaying: false };
    emit();
  });
}

export function toggleSounds() {
  const next = !snap.soundsOn;
  if (typeof window !== "undefined") writeChoice(window.localStorage, SOUNDS_KEY, next);
  snap = { ...snap, soundsOn: next };
  emit();
}

/** A short tone, created only when a sound is actually played. No audio file. */
export function playUiCue(kind: "save" | "alert") {
  if (typeof window === "undefined") return;
  const soundsOn = readChoice(window.localStorage, SOUNDS_KEY);
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!uiSoundAllowed(soundsOn, reduced)) return;
  const Context = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Context) return;
  const ctx = new Context();
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  const start = kind === "save" ? 523.25 : 392;
  const end = kind === "save" ? 659.25 : 523.25;
  osc.type = "sine";
  osc.frequency.setValueAtTime(start, now);
  osc.frequency.exponentialRampToValueAtTime(end, now + 0.09);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.035, now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.16);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.18);
  osc.onended = () => {
    void ctx.close();
  };
}
