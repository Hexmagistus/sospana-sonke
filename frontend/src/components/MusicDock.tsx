"use client";

import { useEffect, useRef, useState, type ComponentType } from "react";

type PanelProps = { open: boolean };

/**
 * Site-wide Music button. The player chunk loads on the first open, then
 * stays mounted for the life of the layout, including client-side navigations.
 * A full page load (the game, or a refresh) starts it again, collapsed.
 */
export default function MusicDock() {
  const [Panel, setPanel] = useState<ComponentType<PanelProps> | null>(null);
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const loading = useRef(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  async function toggle() {
    if (!Panel) {
      if (loading.current) return;
      loading.current = true;
      try {
        const mod = await import("./MusicDockPanel");
        setPanel(() => mod.MusicDockPanel);
        setOpen(true);
      } catch {
        setFailed(true);
      } finally {
        loading.current = false;
      }
      return;
    }
    setOpen((value) => !value);
  }

  return (
    <div className="pointer-events-none fixed bottom-[calc(4.75rem+env(safe-area-inset-bottom))] right-3 z-[35] flex max-w-[calc(100vw-1.5rem)] flex-col items-end gap-2 md:bottom-6 md:right-6">
      {failed ? (
        <p className="pointer-events-auto rounded-xl border border-[#FCC033] bg-[#FFF8EC] px-3 py-2 text-sm text-[#1F2328]" role="status">
          The music player did not load. You can still listen on the{" "}
          <a className="font-semibold text-[#05606F] underline" href="/music">
            music page
          </a>
          .
        </p>
      ) : null}
      {Panel ? <Panel open={open} /> : null}
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls="ss-music-player"
        onClick={toggle}
        className="pointer-events-auto inline-flex min-h-11 items-center gap-2 rounded-full border-2 border-[#1F2328] bg-[#FCC033] px-4 py-2 text-sm font-bold text-[#1F2328] shadow-[0_10px_24px_-14px_rgba(31,35,40,0.7)] hover:bg-[#FFD877] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#067589]"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 18V6l10-2v12" />
          <circle cx="7" cy="18" r="2.25" fill="currentColor" stroke="none" />
          <circle cx="17" cy="16" r="2.25" fill="currentColor" stroke="none" />
        </svg>
        Music
      </button>
    </div>
  );
}
