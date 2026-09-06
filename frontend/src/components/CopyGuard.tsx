"use client";

import { useEffect } from "react";

/**
 * Copy-deterrence layer (UX-only, NOT a security control).
 *
 * Deters casual copying of on-screen content — context menu, text selection,
 * copy/cut, and the common "save/view source" shortcuts. This only raises the
 * effort for a casual visitor; anyone determined can still read the rendered
 * HTML via devtools, "view-source:", or the network tab, so nothing secret must
 * ever rely on this. Deliberately scoped to leave form fields fully usable so
 * login, search and the CV/profile forms keep working normally.
 */
function inEditable(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  if (!el || !el.closest) return false;
  return !!el.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"]');
}

export default function CopyGuard() {
  useEffect(() => {
    const block = (e: Event) => {
      if (!inEditable(e.target)) e.preventDefault();
    };
    const onKey = (e: KeyboardEvent) => {
      if (inEditable(e.target)) return;
      const k = e.key.toLowerCase();
      const mod = e.ctrlKey || e.metaKey;
      if (mod && ["c", "x", "u", "s", "a", "p"].includes(k)) e.preventDefault();
      if (k === "f12") e.preventDefault();
      if (mod && e.shiftKey && ["i", "j", "c"].includes(k)) e.preventDefault();
    };
    document.addEventListener("contextmenu", block);
    document.addEventListener("copy", block);
    document.addEventListener("cut", block);
    document.addEventListener("selectstart", block);
    document.addEventListener("dragstart", block);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("contextmenu", block);
      document.removeEventListener("copy", block);
      document.removeEventListener("cut", block);
      document.removeEventListener("selectstart", block);
      document.removeEventListener("dragstart", block);
      document.removeEventListener("keydown", onKey);
    };
  }, []);
  return null;
}
