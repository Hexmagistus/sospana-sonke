import { roleIdFromCode } from "@/lib/shortLink";

export async function GET(request: Request, { params }: { params: Promise<{ code: string }> }): Promise<Response> {
  const { code } = await params;
  const id = roleIdFromCode(code);
  if (!id) {
    return new Response("Unknown link.\n", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=60" },
    });
  }
  return new Response(null, {
    status: 302,
    headers: {
      Location: new URL(`/jobs/${id}`, request.url).pathname,
      "Cache-Control": "public, max-age=86400",
    },
  });
}
