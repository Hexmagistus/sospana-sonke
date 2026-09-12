"use client";

// A per-browser shortlist of companies/universities the candidate wants to
// come back to. Deliberately local-only (no account sync, no backend table):
// it's just a bookmark list, so there's no reason to make it survive a
// device change, and keeping it out of the database means it works even for
// someone browsing from a shared computer without leaving a server-side
// trail of which employers they're interested in.
const KEY = "sospana_shortlist";
export const SHORTLIST_EVENT = "shortlist-changed";

function read(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

function write(ids: Set<string>) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(Array.from(ids)));
  } catch {
    // Private browsing / storage disabled -- shortlisting just won't persist.
  }
}

export function getShortlist(): Set<string> {
  return read();
}

export function isShortlisted(id: string): boolean {
  return read().has(id);
}

/** Flips the given id's membership and returns the new state. */
export function toggleShortlist(id: string): boolean {
  const ids = read();
  const now = !ids.has(id);
  if (now) ids.add(id);
  else ids.delete(id);
  write(ids);
  if (typeof window !== "undefined") window.dispatchEvent(new Event(SHORTLIST_EVENT));
  return now;
}
