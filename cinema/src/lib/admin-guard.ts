import "server-only";

import { NextResponse } from "next/server";
import { currentAdmin } from "./session";

export async function requireAdmin(): Promise<NextResponse | null> {
  const admin = await currentAdmin();
  if (!admin) return NextResponse.json({ error: "Admin sign-in is required." }, { status: 401 });
  return null;
}
