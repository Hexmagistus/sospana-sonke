import { NextResponse } from "next/server";
import { passwordsMatch, signSession } from "@/lib/auth";
import { rateLimit } from "@/lib/rate-limit";
import { ADMIN_COOKIE } from "@/lib/session";

export async function POST(request: Request) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
  const limited = rateLimit(`admin-login:${ip}`, 8, 15 * 60 * 1000);
  if (!limited.ok) {
    return NextResponse.json(
      { error: `Too many sign-in attempts. Try again in ${limited.retryAfterSeconds} seconds.` },
      { status: 429 },
    );
  }
  const email = process.env.ADMIN_EMAIL;
  const password = process.env.ADMIN_PASSWORD;
  const secret = process.env.ADMIN_SESSION_SECRET;
  if (!email || !password || !secret) {
    return NextResponse.json(
      { error: "Admin sign-in is not configured. Set ADMIN_EMAIL, ADMIN_PASSWORD and ADMIN_SESSION_SECRET." },
      { status: 503 },
    );
  }
  let body: { email?: string; password?: string };
  try {
    body = (await request.json()) as { email?: string; password?: string };
  } catch {
    return NextResponse.json({ error: "The sign-in body was not valid JSON." }, { status: 400 });
  }
  if (body.email !== email || !passwordsMatch(String(body.password ?? ""), password)) {
    return NextResponse.json({ error: "Those admin details were not accepted." }, { status: 401 });
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.set(ADMIN_COOKIE, signSession(email, secret), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return response;
}
