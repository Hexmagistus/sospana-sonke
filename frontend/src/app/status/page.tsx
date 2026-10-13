import type { Metadata } from "next";
import Link from "next/link";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export const metadata: Metadata = {
  title: "Status",
  description: "Whether the API, the database check, and the careers scanner are answering.",
  alternates: { canonical: "/status" },
};

type Scanner = {
  status?: string;
  latest_finished_at?: string | null;
  age_minutes?: number | null;
  schedule_minutes?: number;
  stale_after_minutes?: number;
  failure_threshold?: number;
  sources_at_failure_threshold?: number;
};

type Report = {
  status?: string;
  checked_at?: string;
  components?: {
    api?: { status?: string };
    database?: { status?: string };
    scanner?: Scanner;
  };
};

async function load(): Promise<Report | null> {
  try {
    const res = await fetch(`${API}/status`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = (await res.json()) as Report;
    if (!body || typeof body.status !== "string" || !body.components) return null;
    return body;
  } catch {
    return null;
  }
}

function line(label: string, value: string) {
  return (
    <div className="flex flex-wrap justify-between gap-2 border-b border-ss-border py-2 text-sm">
      <dt className="font-semibold text-ss-text">{label}</dt>
      <dd className="text-ss-muted">{value}</dd>
    </div>
  );
}

export default async function StatusPage() {
  const report = await load();
  const scanner = report?.components?.scanner;
  return (
    <article className="mx-auto max-w-3xl space-y-4">
      <header className="space-y-2">
        <p className="text-sm font-semibold text-ss-primary">Operations</p>
        <h1 className="font-display text-3xl font-bold text-ss-text">Status</h1>
        <p className="text-sm leading-relaxed text-ss-muted">
          This page reads <code>/api/v1/status</code>. The database line is a <code>SELECT 1</code>.
          The scanner line is the newest finished scan. <code>/health</code> does not touch the database.
        </p>
      </header>
      {!report ? (
        <div className="ss-empty" role="status">
          <p className="font-semibold text-ss-text">The status check could not be reached</p>
          <p className="mt-2 text-sm text-ss-muted">No substitute figure is shown.</p>
        </div>
      ) : (
        <dl className="ss-card">
          {line("Overall", report.status || "")}
          {line("Checked", report.checked_at || "")}
          {line("API", report.components?.api?.status || "")}
          {line("Database", report.components?.database?.status || "")}
          {line("Scanner", scanner?.status || "")}
          {line("Newest scan", scanner?.latest_finished_at || "none recorded")}
          {line("Scan age (minutes)", scanner?.age_minutes == null ? "none recorded" : String(scanner.age_minutes))}
          {line("Schedule (minutes)", scanner?.schedule_minutes == null ? "" : String(scanner.schedule_minutes))}
          {line("Stale after (minutes)", scanner?.stale_after_minutes == null ? "" : String(scanner.stale_after_minutes))}
          {line(
            "Sources at the failure threshold",
            scanner?.sources_at_failure_threshold == null
              ? ""
              : `${scanner.sources_at_failure_threshold} (threshold ${scanner.failure_threshold ?? ""})`,
          )}
        </dl>
      )}
      <p className="text-sm text-ss-muted">
        <Link href="/jobs" className="font-semibold text-navy underline">Jobs</Link>
        {" · "}
        <a href={`${API}/status`} className="font-semibold text-navy underline">API status</a>
      </p>
    </article>
  );
}
