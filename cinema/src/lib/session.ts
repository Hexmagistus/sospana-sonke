import "server-only";

import { cookies } from "next/headers";
import { readSession } from "./auth";

export const ADMIN_COOKIE = "sc_admin";

export async function currentAdmin(): Promise<{ email: string } | null> {
  const secret = process.env.ADMIN_SESSION_SECRET;
  if (!secret) return null;
  const jar = await cookies();
  const session = readSession(jar.get(ADMIN_COOKIE)?.value, secret);
  return session ? { email: session.email } : null;
}
