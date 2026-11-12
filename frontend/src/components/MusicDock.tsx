"use client";

import { useEffect, useRef, useState, type ComponentType } from "react";

type PanelProps = { open: boolean; onClose: () => void };

/**
 * Slim Music control directly under the header. Closed, it is one short row
 * and loads no player. The player chunk stays mounted after the first open,
 * including across client-side navigations. A full page load starts it closed.
 */
export default function MusicDock() {
  const [Panel, setPanel] = useState<ComponentType<PanelProps> | null>(null);
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const loading = useRef(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  function close() {
    setOpen(false);
    buttonRef.current?.focus();
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  async function toggle() {
    if (open) {
      close();
      return;
    }
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
    setOpen(true);
  }

  return (
    <div className="border-b border-[#FCC033]/70 bg-ss-surface">
      <div className="mx-auto flex max-w-6xl items-center px-3 py-1 min-[360px]:px-4">
        <button
          ref={buttonRef}
          type="button"
          aria-expanded={open}
          aria-controls="ss-music-player"
          onClick={toggle}
          className="inline-flex h-8 items-center gap-1.5 rounded-full px-2 text-sm font-semibold text-[#1F2328] hover:bg-[#FCF5E5] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#067589]"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 text-[#7A5200]" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 18V6l10-2v12" />
            <circle cx="7" cy="18" r="2.25" fill="currentColor" stroke="none" />
            <circle cx="17" cy="16" r="2.25" fill="currentColor" stroke="none" />
          </svg>
          Music
        </button>
      </div>
      {failed ? (
        <p className="mx-auto max-w-6xl px-3 pb-2 text-sm text-[#1F2328] min-[360px]:px-4" role="status">
          The player did not load. You can still{" "}
          <a className="font-semibold text-[#05606F] underline" href="/music">
            listen on the music page
          </a>
          .
        </p>
      ) : null}
      {Panel ? (
        <div
          className={
            open
              ? "mx-auto max-w-6xl px-3 pb-3 min-[360px]:px-4"
              : "pointer-events-none fixed left-[-12000px] top-0 h-[24rem] w-[22rem] overflow-hidden"
          }
        >
          <Panel open={open} onClose={close} />
        </div>
      ) : null}
    </div>
  );
}
