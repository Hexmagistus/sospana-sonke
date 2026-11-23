import { NextResponse } from "next/server";
import { newId } from "@/lib/auth";
import { getPublicCatalog } from "@/lib/public-catalog";
import { rateLimit } from "@/lib/rate-limit";
import { saveTakedown } from "@/lib/store";
import { insertTakedownRemote, supabaseUrlSet } from "@/lib/supabase-admin";
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
  if (supabaseUrlSet()) {
    try {
      const via = await insertTakedownRemote(takedown);
      return NextResponse.json({
        id: takedown.id,
        detail: via === "service" ? "Stored in Supabase." : "Stored in Supabase with the public insert-only policy.",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return NextResponse.json({ error: message }, { status: 502 });
    }
  }
  try {
    saveTakedown(takedown);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `The complaint could not be saved on this server: ${message}. Set SUPABASE_URL and a Supabase key to store complaints.` },
      { status: 503 },
    );
  }
  return NextResponse.json({
    id: takedown.id,
    detail: "Stored in the demonstration file on this server. Supabase is not configured.",
  });
}

export async function GET() {
  return NextResponse.json({ error: "Complaints are not public." }, { status: 405 });
}
