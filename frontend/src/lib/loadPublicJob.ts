import type { PublicJob } from "./jobPosting";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export type PublicJobDetail = PublicJob & { summary: string };

export const CLOSED_OPPORTUNITY_HEADING = "This opportunity has closed";

export async function loadPublicJob(id: string): Promise<PublicJobDetail | null | "down" | "closed"> {
  try {
    const res = await fetch(`${API}/jobs/${encodeURIComponent(id)}`, { next: { revalidate: 60 } });
    if (res.status === 410) return "closed";
    if (res.status === 404) return null;
    if (!res.ok) return "down";
    const data = (await res.json()) as PublicJobDetail;
    if (!data || typeof data.title !== "string" || typeof data.summary !== "string" || data.is_open !== true) {
      return "down";
    }
    return data;
  } catch {
    return "down";
  }
}
