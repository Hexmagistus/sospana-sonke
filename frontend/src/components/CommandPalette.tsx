"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { queueAgentCommand } from "@/lib/agentHandoff";

/** SOSPANA COMMAND -- a genuine keyboard-accessible navigation/search
 * interface (brief section 10), not a decorative overlay: every entry here
 * either routes straight to a real page or hands a real phrase to the
 * Career Agent's own existing intent parser (see agent/page.tsx's
 * `classifyIntent` -- these strings are copied verbatim from its own quick-
 * action buttons so they're guaranteed to be understood the same way).
 */

interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  run: (router: ReturnType<typeof useRouter>) => void;
}

function toAgent(text: string) {
  return (router: ReturnType<typeof useRouter>) => {
    queueAgentCommand(text);
    router.push("/agent");
  };
}

const BASE_COMMANDS: CommandItem[] = [
  { id: "apply", label: "Show jobs I can apply for", hint: "Career Agent", run: toAgent("Find jobs I can apply for") },
  { id: "almost", label: "Show jobs I'm almost qualified for", hint: "Career Agent", run: toAgent("Show jobs I'm almost qualified for") },
  { id: "employers", label: "Employers in my field", hint: "Career Agent", run: toAgent("Show employers in my field I can apply to directly") },
  { id: "discover", label: "Discover related careers for me", hint: "Career Agent", run: toAgent("Discover related careers for me") },
  { id: "explorer", label: "Explore my qualification", hint: "Career Explorer", run: toAgent("career explorer") },
  { id: "applications", label: "Open my applications", hint: "Application tracker", run: (r) => r.push("/tailor/applications") },
  { id: "matches", label: "My matches", hint: "Saved & scored", run: (r) => r.push("/matches") },
  { id: "cv", label: "Build my CV", hint: "CV Builder", run: (r) => r.push("/master-cv") },
  { id: "companies", label: "Browse the employer directory", hint: "Companies", run: (r) => r.push("/companies") },
  { id: "universities", label: "Browse universities", hint: "Universities", run: (r) => r.push("/universities") },
  { id: "profile", label: "My profile", run: (r) => r.push("/profile") },
  { id: "notifications", label: "Notifications", run: (r) => r.push("/notifications") },
  { id: "dashboard", label: "My dashboard", run: (r) => r.push("/dashboard") },
];

export default function CommandPalette() {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const isK = e.key === "k" || e.key === "K";
      if ((e.metaKey || e.ctrlKey) && isK) {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setHighlight(0);
      // Focus after the modal has actually mounted.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return BASE_COMMANDS;
    return BASE_COMMANDS.filter((c) => c.label.toLowerCase().includes(q));
  }, [query]);

  if (!user) return null;

  function runFreeTextSearch() {
    const text = query.trim();
    if (!text) return;
    queueAgentCommand(text);
    router.push("/agent");
    setOpen(false);
  }

  function runHighlighted() {
    const item = filtered[highlight];
    if (item) {
      item.run(router);
      setOpen(false);
    } else {
      runFreeTextSearch();
    }
  }

  function onKeyDownInput(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      runHighlighted();
    }
  }

  return (
    <>
      {/* Trigger -- always-visible (all breakpoints) so this is a real feature
          on touch devices too, not just a keyboard shortcut (brief section 10).
          bottom-24 on mobile clears the fixed MobileBottomNav bar; md:bottom-6
          drops back down once that bar disappears (md:hidden) at desktop width. */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open Sospana Command (Ctrl+K)"
        className="fixed bottom-24 right-4 z-40 flex items-center gap-1.5 rounded-full border border-ss-border bg-ss-glass px-3.5 py-2 text-xs font-semibold text-ss-text shadow-lg backdrop-blur-md transition hover:-translate-y-0.5 hover:shadow-xl md:bottom-6"
      >
        <span aria-hidden="true">⌘</span> Search
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[60] flex items-start justify-center bg-black/50 px-4 pt-[12vh] backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Sospana Command"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg overflow-hidden rounded-2xl border border-ss-border bg-ss-elevated shadow-2xl"
          >
            <div className="flex items-center gap-2 border-b border-ss-border px-4 py-3">
              <span className="text-ss-muted" aria-hidden="true">⌕</span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setHighlight(0);
                }}
                onKeyDown={onKeyDownInput}
                placeholder="Search opportunities, or jump to a page…"
                className="w-full bg-transparent text-sm text-ss-text placeholder:text-ss-muted focus:outline-none"
              />
              <span className="rounded border border-ss-border px-1.5 py-0.5 text-[10px] font-semibold text-ss-muted">ESC</span>
            </div>
            <ul className="max-h-80 overflow-y-auto py-1.5" role="listbox">
              {filtered.length === 0 && query.trim() && (
                <li>
                  <button
                    onClick={runFreeTextSearch}
                    className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm text-ss-text hover:bg-ss-primary-soft"
                  >
                    <span>Search &ldquo;{query.trim()}&rdquo;</span>
                    <span className="text-xs text-ss-muted">Career Agent</span>
                  </button>
                </li>
              )}
              {filtered.map((item, i) => (
                <li key={item.id}>
                  <button
                    onClick={() => {
                      item.run(router);
                      setOpen(false);
                    }}
                    onMouseEnter={() => setHighlight(i)}
                    className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition ${
                      i === highlight ? "bg-ss-primary-soft text-ss-text" : "text-ss-text hover:bg-ss-primary-soft"
                    }`}
                  >
                    <span>{item.label}</span>
                    {item.hint && <span className="text-xs text-ss-muted">{item.hint}</span>}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </>
  );
}
