/** Offline jobs list: the last good list saved on this device, never an expired role. */

export type SavedJob = { id: string; closing_date?: string | null; is_open?: boolean } & Record<string, unknown>;

export type SavedJobs<T extends SavedJob = SavedJob> = { savedAt: string; jobs: T[] };

/** Today as YYYY-MM-DD in South Africa (UTC+2), the site's reference day. */
export function saToday(now: Date = new Date()): string {
  return new Date(now.getTime() + 2 * 3600_000).toISOString().slice(0, 10);
}

/** HARD RULE: a role whose closing date is before today is never shown. */
export function unexpiredJobs<T extends SavedJob>(jobs: T[], today: string = saToday()): T[] {
  return jobs.filter((job) => {
    if (job.is_open === false) return false;
    const closes = typeof job.closing_date === "string" ? job.closing_date.slice(0, 10) : "";
    return !closes || closes >= today;
  });
}

/** "20 Oct 2026" from an ISO stamp, or the raw value when it cannot be read. */
export function savedOnLabel(savedAt: string): string {
  const d = new Date(savedAt);
  if (Number.isNaN(d.getTime())) return savedAt;
  return d.toLocaleDateString("en-ZA", { day: "numeric", month: "short", year: "numeric", timeZone: "Africa/Johannesburg" });
}

export function offlineBanner(savedAt: string): string {
  return `Offline – showing jobs saved on ${savedOnLabel(savedAt)}`;
}

/** Bootstrap rows have no detail page; they link straight to the employer. */
export function isBootstrapJob(id: string): boolean {
  return id.startsWith("bootstrap-");
}

export function parseSaved(raw: string | null): SavedJobs | null {
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as SavedJobs;
    if (!data || typeof data.savedAt !== "string" || !Array.isArray(data.jobs)) return null;
    return data;
  } catch {
    return null;
  }
}
