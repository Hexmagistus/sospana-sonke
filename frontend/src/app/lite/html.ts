const HEADERS = {
  "Content-Type": "text/html; charset=utf-8",
  "Cache-Control": "public, max-age=60",
  "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'",
};

export function liteResponse(html: string): Response {
  return new Response(html, { headers: HEADERS });
}
