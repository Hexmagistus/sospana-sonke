import { liteProgrammesPage } from "@/lib/litePage";
import { liteResponse } from "../html";
import { loadLiteJobs } from "../load";

export const revalidate = 60;

const TYPES = new Set(["job", "internship", "learnership", "bursary", "graduate_programme"]);

export async function GET(request: Request): Promise<Response> {
  const raw = new URL(request.url).searchParams.get("type") || "";
  const type = TYPES.has(raw) ? raw : "";
  const loaded = await loadLiteJobs({ type, offset: 0 });
  const html = liteProgrammesPage({
    type,
    jobs: loaded.ok ? loaded.jobs : null,
    matched: loaded.ok ? loaded.matched : null,
  });
  return liteResponse(html);
}
