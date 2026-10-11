import { linkScope } from "@/lib/linkScope";

/** Short label for the careers URL. The longer explanation is the tooltip. */
export function LinkScopeBadge({ url }: { url?: string | null }) {
  const scope = linkScope(url);
  if (scope.kind === "none") return null;
  return (
    <span
      title={scope.detail}
      className="inline-flex max-w-full items-center rounded-full border border-ss-border bg-ss-surface px-2 py-0.5 text-xs font-semibold text-ss-text"
    >
      {scope.label}
    </span>
  );
}
