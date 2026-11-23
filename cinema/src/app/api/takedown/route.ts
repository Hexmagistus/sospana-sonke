import { NextResponse } from "next/server";
import { newId } from "@/lib/auth";
import { getPublicCatalog } from "@/lib/public-catalog";
import { rateLimit } from "@/lib/rate-limit";
import { saveTakedown } from "@/lib/store";
import { validateTakedown } from "@/lib/validation";

export async function POST(request: Request) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
  const limited = rateLimit(`takedown:${ip}`, 5, 60 * 60 * 1000);
  if (!limited.ok) {
    return NextResponse.json(
      { error: `Too many complaints from this network. Try again in ${limited.retryAfterSeconds} seconds.` },
      { status: 429 },
    );
  }
  let body: Record<string, string>;
  try {
    body = (await request.json()) as Record<string, string>;
  } catch {
    return NextResponse.json({ error: "The complaint body was not valid JSON." }, { status: 400 });
  }
  const catalog = await getPublicCatalog();
  const parsed = validateTakedown({ ...body, knownIds: catalog.movies.map((movie) => movie.slug) });
  if (!parsed.ok) return NextResponse.json({ errors: parsed.errors }, { status: 400 });
  const takedown = {
    id: newId(),
    claimantName: parsed.value.claimantName,
    contactEmail: parsed.value.contactEmail,
    contentId: parsed.value.contentId,
    reason: parsed.value.reason,
    status: "received" as const,
    createdAt: new Date().toISOString(),
  };
  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (supabaseUrl && serviceKey) {
    const response = await fetch(`${supabaseUrl.replace(/\/$/, "")}/rest/v1/takedown_requests`, {
      method: "POST",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "content-type": "application/json",
        prefer: "return=representation",
      },
      body: JSON.stringify({
        claimant_name: takedown.claimantName,
        contact_email: takedown.contactEmail,
        content_id: takedown.contentId,
        reason: takedown.reason,
        status: takedown.status,
      }),
    });
    const text = await response.text();
    if (!response.ok) {
      return NextResponse.json(
        { error: `Supabase rejected the complaint (HTTP ${response.status}): ${text.slice(0, 400)}` },
        { status: 502 },
      );
    }
    return NextResponse.json({ id: takedown.id, detail: "Stored in Supabase." });
  }
  saveTakedown(takedown);
  return NextResponse.json({
    id: takedown.id,
    detail: "Stored in the demonstration file on this server. SUPABASE_SERVICE_ROLE_KEY is not set, so it was not written to Supabase.",
  });
}

export async function GET() {
  return NextResponse.json({ error: "Complaints are not public." }, { status: 405 });
}
