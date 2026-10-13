import { loadPublicJob } from "@/lib/loadPublicJob";
import { SITE_URL } from "@/lib/seo";
import { roleCode, sharePlain } from "@/lib/shortLink";

export const revalidate = 60;

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }): Promise<Response> {
  const { id } = await params;
  const job = await loadPublicJob(id);
  if (job === "down") {
    return new Response("The stored role could not be reached.\n", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  if (!job) {
    return new Response("This stored role is not available.\n", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=60" },
    });
  }
  const code = roleCode(job.id);
  const shortUrl = code ? `${SITE_URL}/go/${code}` : `${SITE_URL}/jobs/${job.id}`;
  return new Response(`${sharePlain(job, shortUrl)}\n`, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=60" },
  });
}
