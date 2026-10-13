import { jobSummary, type PublicJob } from "@/lib/jobPosting";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const revalidate = 60;

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function GET() {
  let jobs: PublicJob[] = [];
  try {
    const res = await fetch(`${API}/jobs?limit=30&max_age_days=7`, { next: { revalidate: 60 } });
    if (res.ok) {
      const data = (await res.json()) as { jobs?: PublicJob[] };
      jobs = Array.isArray(data.jobs) ? data.jobs : [];
    }
  } catch {
    jobs = [];
  }
  const items = jobs.map((job) => {
    const link = `${SITE_URL}/jobs/${job.id}`;
    return `<item><title>${escapeXml(job.title)}</title><link>${link}</link><guid>${link}</guid><pubDate>${escapeXml(job.last_seen_at)}</pubDate><description>${escapeXml(jobSummary(job))}</description></item>`;
  }).join("");
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>${escapeXml(SITE_NAME)} new stored roles</title><link>${SITE_URL}/jobs</link><description>Open roles last seen on the employer site within seven days. A closed role is not included.</description>${items}</channel></rss>`;
  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=60, stale-while-revalidate=120",
    },
  });
}
