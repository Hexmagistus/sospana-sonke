/** A reversible short code for a stored role. No lookup table. */

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function roleCode(id: string): string | null {
  if (!UUID.test(id)) return null;
  return Buffer.from(id.replace(/-/g, ""), "hex").toString("base64url");
}

export function roleIdFromCode(code: string): string | null {
  if (!/^[A-Za-z0-9_-]{22}$/.test(code)) return null;
  const bytes = Buffer.from(code, "base64url");
  if (bytes.length !== 16) return null;
  const hex = bytes.toString("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

type ShareJob = {
  title: string;
  company_name: string;
  company_country?: string | null;
  location?: string | null;
  closing_date?: string | null;
  application_url?: string | null;
};

/** A few lines for WhatsApp or SMS. The short link is always last. */
export function sharePlain(job: ShareJob, shortUrl: string): string {
  const place = [job.location, job.company_country].filter((part): part is string => Boolean(part)).join(", ");
  const lines = [
    job.title.trim().slice(0, 120),
    job.company_name.trim().slice(0, 80),
    place.slice(0, 80),
    job.closing_date ? `Closes ${job.closing_date.slice(0, 10)}` : "",
    job.application_url ? `Apply: ${job.application_url}` : "No application link was stored.",
    shortUrl,
  ].filter(Boolean);
  let text = lines.join("\n");
  if (text.length > 480) text = [lines[0], lines[1], shortUrl].filter(Boolean).join("\n");
  return text;
}

export function whatsAppHref(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export function smsHref(text: string): string {
  return `sms:?&body=${encodeURIComponent(text)}`;
}
