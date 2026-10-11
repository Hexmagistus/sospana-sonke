import type { ReactNode } from "react";

/** Shared page title. Same type, spacing and colour on every public and signed-in screen. */
export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="ss-page-header max-w-3xl">
      {eyebrow ? (
        <p className="text-sm font-semibold uppercase tracking-wide text-ss-muted">{eyebrow}</p>
      ) : null}
      <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tight text-ss-text sm:text-4xl">
        {title}
      </h1>
      {children ? <div className="mt-3 space-y-2 text-base leading-relaxed text-ss-muted">{children}</div> : null}
    </header>
  );
}
