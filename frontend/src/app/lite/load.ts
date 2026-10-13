import { FLAGSHIP_COUNTRY, flagshipCountry } from "@/lib/flagship";
import { LITE_LIMIT, type LiteJob } from "@/lib/litePage";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

type List = { ok: true; jobs: LiteJob[]; matched: number } | { ok: false };

export async function loadLiteJobs(search: {
  q?: string;
  country?: string;
  type?: string;
  offset?: number;
}): Promise<List> {
  const params = new URLSearchParams();
  const q = (search.q || "").trim().slice(0, 80);
  if (q) params.set("q", q);
  const country = flagshipCountry(search.country);
  if (country) params.set("country", country);
  if (search.type) params.set("opportunity_type", search.type);
  params.set("limit", String(LITE_LIMIT));
  params.set("offset", String(search.offset || 0));
  try {
    const res = await fetch(`${API}/jobs?${params.toString()}`, { next: { revalidate: 60 } });
    if (!res.ok) return { ok: false };
    const data = (await res.json()) as { jobs?: LiteJob[]; matched?: number };
    if (!data || !Array.isArray(data.jobs) || typeof data.matched !== "number") return { ok: false };
    return { ok: true, jobs: data.jobs, matched: data.matched };
  } catch {
    return { ok: false };
  }
}

export async function loadLiteJob(id: string): Promise<LiteJob | null | "down"> {
  try {
    const res = await fetch(`${API}/jobs/${encodeURIComponent(id)}`, { next: { revalidate: 60 } });
    if (res.status === 404) return null;
    if (!res.ok) return "down";
    const data = (await res.json()) as LiteJob;
    if (!data || typeof data.title !== "string") return "down";
    return data;
  } catch {
    return "down";
  }
}

export async function loadLiteEmployer(id: string): Promise<{
  name: string;
  country: string;
  careersUrl: string;
  openCount: number;
  roles: LiteJob[];
} | null | "down"> {
  try {
    const res = await fetch(`${API}/employers/${encodeURIComponent(id)}`, { next: { revalidate: 300 } });
    if (res.status === 404) return null;
    if (!res.ok) return "down";
    const data = (await res.json()) as {
      company_name?: string;
      country?: string;
      careers_url?: string;
      open_role_count?: number;
      roles?: LiteJob[];
    };
    if (!data || typeof data.company_name !== "string" || typeof data.careers_url !== "string") return "down";
    return {
      name: data.company_name,
      country: data.country || FLAGSHIP_COUNTRY,
      careersUrl: data.careers_url,
      openCount: typeof data.open_role_count === "number" ? data.open_role_count : 0,
      roles: Array.isArray(data.roles) ? data.roles : [],
    };
  } catch {
    return "down";
  }
}
