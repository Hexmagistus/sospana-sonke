/** When the hero may replace its painted globe with a WebGL one. */

import { blocksHeavyMedia } from "./litePage";

export type ShowpieceSignals = {
  reducedMotion: boolean;
  finePointer: boolean;
  wide: boolean;
  saveData: boolean;
  slowConnection: boolean;
  cores: number;
};

export function canMountShowpiece(signals: ShowpieceSignals): boolean {
  if (signals.reducedMotion || signals.saveData || signals.slowConnection) return false;
  if (!signals.finePointer || !signals.wide) return false;
  if (signals.cores > 0 && signals.cores < 4) return false;
  return true;
}

type ConnectionInfo = { saveData?: boolean; effectiveType?: string };

export function readShowpieceSignals(): ShowpieceSignals {
  const connection = (navigator as Navigator & { connection?: ConnectionInfo }).connection;
  const effective = connection?.effectiveType ?? "";
  let stored: string | null = null;
  try {
    stored = window.localStorage.getItem("ss-data-saver");
  } catch {
    stored = null;
  }
  return {
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    finePointer: window.matchMedia("(hover: hover) and (pointer: fine)").matches,
    wide: window.innerWidth >= 1280,
    saveData: blocksHeavyMedia(connection?.saveData === true, stored, window.location.pathname.startsWith("/lite")),
    slowConnection: effective === "slow-2g" || effective === "2g" || effective === "3g",
    cores: navigator.hardwareConcurrency || 0,
  };
}
