import { jobSummary, type PublicJob } from "@/lib/jobPosting";
import { SITE_NAME, SITE_URL } from "@/lib/seo";

export const dynamic = "force-dynamic";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function GET() {
  let jobs: PublicJob[] = [];
  try {
    const res = await fetch(`${API}/jobs?limit=30&max_age_days=7`, { cache: "no-store" });
    if (res.ok) {
      const data = (await res.json()) as { jobs?: PublicJob[] };
      jobs = Array.isArray(data.jobs) ? data.jobs : [];
    }
  } catch {
    jobs = [];
  }
  const body = {
    version: "https://jsonfeed.org/version/1.1",
    title: `${SITE_NAME} new stored roles`,
    home_page_url: `${SITE_URL}/jobs`,
    feed_url: `${SITE_URL}/feed.json`,
    description: "Open roles last seen on the employer site within seven days. A closed role is not included.",
    items: jobs.map((job) => ({
      id: `${SITE_URL}/jobs/${job.id}`,
      url: `${SITE_URL}/jobs/${job.id}`,
      title: job.title,
      content_text: jobSummary(job),
      date_modified: job.last_seen_at,
      authors: [{ name: job.company_name }],
    })),
  };
  return Response.json(body, {
    headers: { "Cache-Control": "public, max-age=300" },
  });
}
