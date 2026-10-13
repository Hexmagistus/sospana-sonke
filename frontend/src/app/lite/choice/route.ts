import { safeReturnPath } from "@/lib/litePage";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const to = url.searchParams.get("to") === "full" ? "full" : "lite";
  const next = safeReturnPath(url.searchParams.get("next"));
  const secure = url.protocol === "https:" ? "; Secure" : "";
  return new Response(null, {
    status: 302,
    headers: {
      Location: next,
      "Cache-Control": "private, no-store",
      "Set-Cookie": `ss-site=${to}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`,
    },
  });
}
