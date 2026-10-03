/**
 * Where a notification row goes when it is activated.
 *
 * Tagged listing links are http(s) only and open in a new tab. Anything else
 * stays inside the app: preferences, a match, an application, and so on.
 * javascript:, credentials in the URL, and protocol-relative links are refused.
 */

export const PREFERENCES_HREF = "/security#notification-preferences";

export type NoticeInput = {
  type: string;
  link_url?: string | null;
  related_type?: string | null;
  related_id?: string | null;
};

export type NoticeTarget =
  | { kind: "internal"; href: string }
  | { kind: "external"; href: string }
  | { kind: "download"; href: string };

export function linkAttrs(target: NoticeTarget): { target?: "_blank"; rel?: "noopener noreferrer" } {
  if (target.kind === "external") return { target: "_blank", rel: "noopener noreferrer" };
  return {};
}

function hasControlChar(text: string): boolean {
  for (let i = 0; i < text.length; i += 1) {
    const code = text.charCodeAt(i);
    if (code < 33 || code === 127) return true;
  }
  return false;
}

/** A same-app path. Refuses //host, backslashes, and javascript: hiding in the path. */
export function safeInternalPath(raw: string): string | null {
  const text = raw.trim();
  if (!text.startsWith("/") || text.startsWith("//") || text.startsWith("/\\")) return null;
  if (text.includes("\\") || hasControlChar(text)) return null;
  const lower = text.toLowerCase();
  if (lower.includes("javascript:") || lower.includes("data:") || lower.includes("vbscript:")) return null;
  const path = text.split(/[?#]/, 1)[0];
  if (path.includes(":")) return null;
  const segments = path.split("/");
  if (segments.some((seg) => seg === "." || seg === "..")) return null;
  return text;
}

/** A plain http(s) URL with a host and no embedded username or password. */
export function safeExternalUrl(raw: string): string | null {
  const text = raw.trim();
  if (!text || text.includes("\\") || hasControlChar(text)) return null;
  let parsed: URL;
  try {
    parsed = new URL(text);
  } catch {
    return null;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
  if (parsed.username || parsed.password) return null;
  if (!parsed.hostname) return null;
  return text;
}

function safeToken(value: string | null | undefined): string | null {
  if (!value) return null;
  const head = value.split(":")[0];
  if (!/^[A-Za-z0-9_-]{1,80}$/.test(head)) return null;
  return head;
}

function pageForType(note: NoticeInput): NoticeTarget {
  const id = safeToken(note.related_id);
  switch (note.type) {
    case "strong_match":
      return { kind: "internal", href: id ? `/matches/${id}` : "/matches" };
    case "action_required":
      return { kind: "internal", href: id ? `/applications/${id}` : "/applications" };
    case "daily_agent_briefing":
      return { kind: "internal", href: "/applications" };
    case "new_jobs":
      return { kind: "internal", href: "/agent" };
    case "report_ready":
      return id
        ? { kind: "download", href: `/reports/${encodeURIComponent(id)}/download` }
        : { kind: "internal", href: "/dashboard" };
    case "link_updated":
      return { kind: "internal", href: id ? `/companies?company=${encodeURIComponent(id)}` : "/companies" };
    case "mention":
      return { kind: "internal", href: "/companies" };
    case "source_alert":
      return { kind: "internal", href: "/admin" };
    case "consent_choices":
      return { kind: "internal", href: PREFERENCES_HREF };
    default:
      return { kind: "internal", href: "/notifications" };
  }
}

export function notificationTarget(note: NoticeInput): NoticeTarget {
  // The preferences notice always stays on our page, even when the stored
  // link is an absolute copy of that same address.
  if (note.type === "consent_choices") {
    return { kind: "internal", href: PREFERENCES_HREF };
  }
  const link = (note.link_url || "").trim();
  if (link) {
    const internal = safeInternalPath(link);
    if (internal) return { kind: "internal", href: internal };
    const external = safeExternalUrl(link);
    if (external) return { kind: "external", href: external };
  }
  return pageForType(note);
}
