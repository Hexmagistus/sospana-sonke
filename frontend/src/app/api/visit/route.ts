import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { hashVisitor, recordVisits, saDay, visitStoreConfigured, type Visit } from "@/lib/visitStore";

export const dynamic = "force-dynamic";

const COOKIE = "ss_vid";
const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Records page views without Neon. Body: { visits: [{ day, path }] } (a batch, so views queued
 * in the browser while offline are sent later). Stores daily totals and a hashed anonymous
 * visitor id only: no IP addresses, no raw cookie ids. Returns 503 when no store is set up, and
 * the browser keeps the queue.
 */
export async function POST(req: NextRequest) {
  if (!visitStoreConfigured) return NextResponse.json({ ok: false, reason: "store-not-configured" }, { status: 503 });
  let body: { visits?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 });
  }
  const today = saDay(new Date());
  const oldest = saDay(new Date(Date.now() - 60 * 86400000));
  const visits: Visit[] = (Array.isArray(body.visits) ? body.visits : [])
    .slice(0, 200)
    .map((v) => v as { day?: unknown; path?: unknown })
    .filter((v) => typeof v.day === "string" && DAY_RE.test(v.day) && v.day <= today && v.day >= oldest)
    .map((v) => ({ day: v.day as string, path: typeof v.path === "string" ? v.path.split("?")[0].slice(0, 120) || "/" : "/" }));
  if (visits.length === 0) return NextResponse.json({ ok: true, recorded: 0 });

  const existing = req.cookies.get(COOKIE)?.value;
  const id = existing && /^[0-9a-f-]{36}$/.test(existing) ? existing : randomUUID();
  try {
    await recordVisits(hashVisitor(id), visits);
  } catch {
    return NextResponse.json({ ok: false, reason: "store-unreachable" }, { status: 503 });
  }
  const res = NextResponse.json({ ok: true, recorded: visits.length });
  if (!existing) {
    res.cookies.set(COOKIE, id, { httpOnly: true, sameSite: "lax", secure: true, path: "/", maxAge: 365 * 86400 });
  }
  return res;
}
