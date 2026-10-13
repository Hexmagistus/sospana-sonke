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
    <header className="ss-hero ss-intel ss-page-header max-w-3xl rounded-3xl px-5 py-8 sm:px-8">
      {eyebrow ? (
        <p className="ss-intel-accent text-sm font-semibold uppercase tracking-wide">{eyebrow}</p>
      ) : null}
      <h1 className="ss-intel-title mt-1 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
        {title}
      </h1>
      {children ? <div className="ss-intel-lead mt-3 space-y-2 text-base leading-relaxed">{children}</div> : null}
    </header>
  );
}
