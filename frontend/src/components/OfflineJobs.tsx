"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import type { PublicJob } from "@/lib/jobPosting";
import { isBootstrapJob, offlineBanner, parseSaved, saToday, unexpiredJobs, type SavedJobs } from "@/lib/offlineJobs";

const CACHE = "ss-saved-jobs";
const KEY = "/__saved-jobs";

async function readSaved(): Promise<SavedJobs | null> {
  try {
    if ("caches" in window) {
      const hit = await (await caches.open(CACHE)).match(KEY);
      if (hit) return parseSaved(await hit.text());
    }
  } catch { /* fall through */ }
  try {
    return parseSaved(window.localStorage.getItem(CACHE));
  } catch {
    return null;
  }
}

async function writeSaved(data: SavedJobs): Promise<void> {
  const raw = JSON.stringify(data);
  try {
    if ("caches" in window) {
      await (await caches.open(CACHE)).put(KEY, new Response(raw, { headers: { "Content-Type": "application/json" } }));
      return;
    }
  } catch { /* fall through */ }
  try { window.localStorage.setItem(CACHE, raw); } catch { /* storage full or blocked */ }
}

/** Keeps the latest good list on this device for offline use. Renders nothing. */
export function SaveJobs({ jobs }: { jobs: PublicJob[] }) {
  useEffect(() => {
    const open = unexpiredJobs(jobs);
    if (open.length > 0) void writeSaved({ savedAt: new Date().toISOString(), jobs: open });
  }, [jobs]);
  return null;
}

export function OfflineBanner({ savedAt }: { savedAt: string }) {
  return (
    <p role="status" className="rounded-xl border-2 border-[#d4a017] bg-[#fff8e1] px-4 py-2 text-sm font-semibold text-[#0c1b33]">
      {offlineBanner(savedAt)}
    </p>
  );
}

/**
 * A page served from the offline cache may be days old. Hide any card whose
 * closing date has passed since it was rendered.
 */
export function ExpiryGuard() {
  useEffect(() => {
    const today = saToday();
    document.querySelectorAll<HTMLElement>("[data-closes]").forEach((el) => {
      const closes = el.dataset.closes || "";
      if (closes && closes < today) el.hidden = true;
    });
  }, []);
  return null;
}

export function JobTitleLink({ job }: { job: PublicJob }) {
  if (isBootstrapJob(job.id) && job.application_url) {
    return <a href={job.application_url} rel="noopener noreferrer" target="_blank" className="underline">{job.title}</a>;
  }
  return <Link href={`/jobs/${job.id}`} className="underline">{job.title}</Link>;
}

type State = { kind: "loading" } | { kind: "none" } | { kind: "jobs"; jobs: PublicJob[]; savedAt: string | null };

/** Shown when the server could not load the list: try the browser, then the saved copy. */
export function OfflineJobsFallback({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs?limit=30`);
        if (res.ok) {
          const data = (await res.json()) as { jobs?: PublicJob[]; from_snapshot?: boolean; snapshot_saved_at?: string | null };
          const jobs = unexpiredJobs(Array.isArray(data.jobs) ? data.jobs : []);
          if (jobs.length > 0) {
            if (!data.from_snapshot) void writeSaved({ savedAt: new Date().toISOString(), jobs });
            if (live) setState({ kind: "jobs", jobs, savedAt: data.from_snapshot ? data.snapshot_saved_at || null : null });
            return;
          }
        }
      } catch { /* offline */ }
      const saved = await readSaved();
      const jobs = saved ? (unexpiredJobs(saved.jobs) as unknown as PublicJob[]) : [];
      if (!live) return;
      setState(saved && jobs.length > 0 ? { kind: "jobs", jobs, savedAt: saved.savedAt } : { kind: "none" });
    })();
    return () => { live = false; };
  }, []);

  if (state.kind === "loading") return <p className="text-sm text-ss-muted" role="status">Loading saved roles.</p>;
  if (state.kind === "none") return <>{children}</>;
  return (
    <div className="space-y-3">
      {state.savedAt ? <OfflineBanner savedAt={state.savedAt} /> : null}
      <ul className="grid gap-3">
        {state.jobs.map((job) => (
          <li key={job.id} className="ss-card">
            <h2 className="font-display text-xl font-bold text-ss-text"><JobTitleLink job={job} /></h2>
            <p className="mt-1 text-sm text-ss-muted">
              {job.company_name}{job.location ? ` · ${job.location}` : ""}
            </p>
            <p className="mt-2 text-xs text-ss-muted">
              {job.closing_date ? `Closes ${job.closing_date}` : "No closing date stated"}
            </p>
            {job.application_url ? (
              <a href={job.application_url} rel="noopener noreferrer" target="_blank" className="mt-3 inline-flex text-sm font-semibold text-navy underline">
                Apply on the employer&apos;s page
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
