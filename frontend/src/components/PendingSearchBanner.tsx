"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getPendingSearch, clearPendingSearch, queueAgentCommand } from "@/lib/agentHandoff";

/** Picks up a search typed into the public homepage's search console before
 * the visitor signed up (see page.tsx's HeroSearchConsole), and offers to
 * continue it in the Career Agent now that they're logged in and have
 * landed here (login/register both redirect to /companies). Renders nothing
 * when there's no pending search -- most visits. */
export default function PendingSearchBanner() {
  const router = useRouter();
  const [text, setText] = useState<string | null>(null);

  useEffect(() => {
    setText(getPendingSearch());
  }, []);

  if (!text) return null;

  function continueSearch() {
    queueAgentCommand(text!);
    clearPendingSearch();
    router.push("/agent");
  }

  function dismiss() {
    clearPendingSearch();
    setText(null);
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-ss-primary-border-soft bg-ss-primary-soft px-5 py-3.5 text-sm">
      <span className="text-ss-text">
        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-ss-primary align-middle" aria-hidden="true" />
        Pick up where you left off — you searched for <strong>&ldquo;{text}&rdquo;</strong>.
      </span>
      <div className="flex shrink-0 items-center gap-2">
        <button
          onClick={continueSearch}
          className="rounded-lg bg-ss-primary px-3.5 py-1.5 text-xs font-bold text-[#3a2b00] shadow-sm transition hover:brightness-105"
        >
          Continue in Career Agent →
        </button>
        <button onClick={dismiss} aria-label="Dismiss" className="rounded-md px-2 py-1 text-ss-muted transition hover:text-ss-text">
          ✕
        </button>
      </div>
    </div>
  );
}
