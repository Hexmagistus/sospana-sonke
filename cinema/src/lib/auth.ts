import { createHmac, randomBytes, scryptSync, timingSafeEqual } from "node:crypto";

const SALT = "sospana-cinema-admin-v1";

export function passwordsMatch(input: string, expected: string): boolean {
  const left = scryptSync(input, SALT, 32, { N: 16384, r: 8, p: 1 });
  const right = scryptSync(expected, SALT, 32, { N: 16384, r: 8, p: 1 });
  return timingSafeEqual(left, right);
}

type SessionPayload = { email: string; exp: number };

export function signSession(email: string, secret: string, ttlSeconds = 60 * 60 * 12): string {
  const payload: SessionPayload = { email, exp: Math.floor(Date.now() / 1000) + ttlSeconds };
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = createHmac("sha256", secret).update(body).digest("base64url");
  return `${body}.${sig}`;
}

export function readSession(token: string | undefined, secret: string): SessionPayload | null {
  if (!token || !secret) return null;
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  const expected = createHmac("sha256", secret).update(body).digest("base64url");
  const left = Buffer.from(sig);
  const right = Buffer.from(expected);
  if (left.length !== right.length || !timingSafeEqual(left, right)) return null;
  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as SessionPayload;
    if (!payload.email || typeof payload.exp !== "number") return null;
    if (payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

export function newId(): string {
  return randomBytes(12).toString("hex");
}
