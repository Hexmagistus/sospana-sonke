import CountOutboundLink from "@/components/CountOutboundLink";

/** The real next step for a stored role: read it here, open the source, apply there. */
export function ApplySteps({
  applicationUrl,
  vacancyId,
  onDark = false,
}: {
  applicationUrl: string | null;
  vacancyId?: string;
  /** Teal-on-navy when the card sits on the midnight band. */
  onDark?: boolean;
}) {
  const quiet = onDark ? "text-[#d5dde8]" : "text-ss-muted";
  const ink = onDark ? "text-white" : "text-ss-text";
  return (
    <div className="mt-3">
      <p className={`text-sm font-semibold ${ink}`}>How to apply</p>
      <ol className={`mt-1 list-decimal space-y-1 pl-5 text-sm leading-relaxed ${quiet}`}>
        <li>Read the summary on this page. It is not the full advert.</li>
        <li>
          {applicationUrl ? (
            <CountOutboundLink
              href={applicationUrl}
              targetKind="vacancy"
              targetId={vacancyId}
              className={onDark ? "font-semibold text-[#5eead4] underline" : "font-semibold text-[#0f766e] underline"}
            >
              Open the source page
            </CountOutboundLink>
          ) : (
            "No application link was stored for this role."
          )}
        </li>
        <li>Apply on that page. Sospana Sonke does not send an application for you.</li>
      </ol>
    </div>
  );
}
