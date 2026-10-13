import { liteSearchPage } from "@/lib/litePage";
import { liteResponse } from "./html";
import { loadLiteJobs } from "./load";

export const revalidate = 60;

function offsetOf(value: string | null): number {
  const offset = Number(value || "0");
  return Number.isInteger(offset) && offset >= 0 && offset <= 500 ? offset : 0;
}

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const q = url.searchParams.get("q") || "";
  const country = url.searchParams.get("country") ?? undefined;
  const offset = offsetOf(url.searchParams.get("offset"));
  const loaded = await loadLiteJobs({ q, country, offset });
  const html = liteSearchPage({
    q,
    country,
    jobs: loaded.ok ? loaded.jobs : null,
    matched: loaded.ok ? loaded.matched : null,
    offset,
  });
  return liteResponse(html);
}
