/** Where to send someone after sign-in.

Only a path we generated is accepted: the directory, or a public country page.
Anything else, including another site, stays on the directory home.
*/

const ORIGIN = "https://sospana-sonke.vercel.app";

export function safeInternalPath(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const value = raw.trim();
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return null;
  if (/[\u0000-\u001f\u007f]/.test(value)) return null;
  let url: URL;
  try {
    url = new URL(value, ORIGIN);
  } catch {
    return null;
  }
  if (url.origin !== ORIGIN || url.username || url.password) return null;
  const path = url.pathname;
  const allowed = path === "/companies"
    || path === "/countries"
    || (path.startsWith("/countries/") && path.length > "/countries/".length);
  if (!allowed) return null;
  return `${path}${url.search}`;
}
