/** Same gate as cinema/discovery. NC and ND licences are refused. */

const REJECT = ["by-nc", "by-nd", "nc-sa", "nc-nd"];

export function licenceKind(url: string | null | undefined): string | null {
  if (!url) return null;
  const value = url.trim().toLowerCase();
  if (!value.startsWith("http://") && !value.startsWith("https://")) return null;
  if (REJECT.some((part) => value.includes(part))) return null;
  if (value.includes("publicdomain/zero") || value.endsWith("/zero/1.0") || value.endsWith("/zero/1.0/")) {
    return "cc0";
  }
  if (
    value.includes("publicdomain/mark") ||
    value.includes("public-domain") ||
    value.includes("/licenses/publicdomain") ||
    value.endsWith("/publicdomain") ||
    value.endsWith("/publicdomain/")
  ) {
    return "public-domain";
  }
  if (value.includes("/licenses/by-sa/") || value.endsWith("/licenses/by-sa")) return "cc-by-sa";
  if (value.includes("/licenses/by/") || value.endsWith("/licenses/by")) return "cc-by";
  return null;
}

const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._-]{0,180}$/;

export function archiveCandidate(item: {
  identifier?: string;
  title?: string;
  licenseurl?: string;
}): { title: string; identifier: string; licenceType: string; authorizedEmbedUrl: string; licenceEvidenceUrl: string } | null {
  const kind = licenceKind(item.licenseurl);
  const identifier = item.identifier?.trim() ?? "";
  const title = typeof item.title === "string" ? item.title.trim() : "";
  if (!kind || !title || !IDENTIFIER.test(identifier) || !item.licenseurl) return null;
  return {
    title,
    identifier,
    licenceType: kind,
    licenceEvidenceUrl: item.licenseurl,
    authorizedEmbedUrl: `https://archive.org/embed/${identifier}`,
  };
}
