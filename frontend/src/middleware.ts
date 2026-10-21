import { NextResponse, type NextRequest } from "next/server";

// Cheap first-line filter for the public directory pages. Real rate limiting is
// done by Vercel Firewall rules (free plan) because Edge middleware has no shared
// memory between instances. This only rejects obvious tooling user agents.
const BAD_UA = /(python-requests|python-urllib|aiohttp|httpx|scrapy|curl\/|wget|go-http-client|java\/|okhttp|libwww-perl|node-fetch|axios|headlesschrome|phantomjs|GPTBot|CCBot|Bytespider|ClaudeBot|PerplexityBot|AhrefsBot|SemrushBot|MJ12bot|DataForSeoBot)/i;

export function middleware(req: NextRequest) {
  const ua = req.headers.get("user-agent") || "";
  if (!ua || BAD_UA.test(ua)) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  const res = NextResponse.next();
  res.headers.set("X-Robots-Tag", "noai, noimageai");
  return res;
}

export const config = {
  matcher: ["/sa-careers", "/careers/:path*", "/employers/:path*"],
};
