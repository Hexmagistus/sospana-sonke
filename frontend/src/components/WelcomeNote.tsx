"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const STORAGE_KEY = "ss-welcome-dismissed";

/** A first-visit note. Dismissing it only hides the note on this device. */
export default function WelcomeNote() {
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    try {
      if (window.localStorage.getItem(STORAGE_KEY) !== "1") setOpen(true);
    } catch {
      setOpen(true);
    }
  }, []);

  function dismiss() {
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* the note stays hidden for this view either way */
    }
    setOpen(false);
    setToast("Welcome note hidden on this device.");
  }

  if (!open && !toast) return null;

  return (
    <div className="mx-auto mt-6 w-full max-w-lg space-y-2 md:pointer-events-none md:fixed md:inset-x-0 md:bottom-6 md:z-30 md:mt-0 md:px-4">
      {open ? (
        <aside className="ss-intel-card pointer-events-auto shadow-lg" aria-label="Welcome">
          <p className="text-base font-bold text-[#0c1b33]">New here? Three steps.</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed text-[#3f4a5c]">
            <li>
              <Link href="/jobs" className="font-semibold text-[#0f766e] underline">Search stored roles</Link>
              , including internships, learnerships, bursaries and graduate programmes.
            </li>
            <li>Open the employer&apos;s own page from the result.</li>
            <li>Apply there. Nothing is sent for you, and this note is not required.</li>
          </ol>
          <button
            type="button"
            onClick={dismiss}
            className="mt-3 inline-flex min-h-11 items-center rounded-xl bg-[#0c1b33] px-4 py-2 text-sm font-semibold text-white"
          >
            Hide this note
          </button>
        </aside>
      ) : null}
      {toast ? (
        <p role="status" className="pointer-events-auto rounded-xl bg-[#0c1b33] px-4 py-3 text-sm font-semibold text-white">
          {toast}
        </p>
      ) : null}
    </div>
  );
}
