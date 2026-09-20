"use client";

import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes } from "react";
import Link from "next/link";

type Accent = "teal" | "gold" | "coral" | "purple" | "sky" | "navy";

const ACCENT_LEFT: Record<Accent, string> = {
  teal: "border-l-brand",
  gold: "border-l-gold",
  coral: "border-l-coral",
  purple: "border-l-purple",
  sky: "border-l-sky",
  navy: "border-l-navy",
};

export function Card({
  children,
  className = "",
  accent,
  interactive = false,
}: {
  children: ReactNode;
  className?: string;
  accent?: Accent;
  /** Adds a hover lift + shadow, for cards that represent a clickable/selectable item. */
  interactive?: boolean;
}) {
  const accentCls = accent ? `border-l-4 ${ACCENT_LEFT[accent]}` : "";
  const interactiveCls = interactive ? "hover:-translate-y-0.5 hover:border-ss-tech hover:shadow-[0_0_0_1px_var(--ss-tech-glow),0_22px_60px_-22px_var(--ss-tech-glow)]" : "";
  return (
    <div
      className={`ss-card-neon rounded-2xl border border-ss-border bg-ss-surface p-5 text-ss-text shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-300 ${accentCls} ${interactiveCls} ${className}`}
    >
      {children}
    </div>
  );
}

/** Small technical-vocabulary indicator -- "● LIVE", "● VERIFIED",
 * "UPDATED 12 MIN AGO" -- for surfacing real, already-computed freshness/
 * status facts (never a decorative label) in a consistent, restrained way.
 * A dot (colour-coded by tone) plus uppercase small-caps text; tone also
 * carries the meaning so this never relies on colour alone. */
type StatusTone = "live" | "verified" | "new" | "closing" | "matched" | "saved" | "neutral";

const STATUS_TONE: Record<StatusTone, { dot: string; text: string }> = {
  live: { dot: "bg-ss-success", text: "text-ss-success" },
  verified: { dot: "bg-ss-tech", text: "text-ss-tech" },
  new: { dot: "bg-ss-primary", text: "text-ss-primary" },
  closing: { dot: "bg-ss-danger", text: "text-ss-danger" },
  matched: { dot: "bg-ss-tech", text: "text-ss-tech" },
  saved: { dot: "bg-ss-primary", text: "text-ss-primary" },
  neutral: { dot: "bg-ss-muted", text: "text-ss-muted" },
};

export function StatusBadge({
  tone = "neutral",
  pulse = false,
  children,
}: {
  tone?: StatusTone;
  /** A soft ping animation for a genuinely "live"/real-time fact -- off by
   * default, and respects prefers-reduced-motion globally. */
  pulse?: boolean;
  children: ReactNode;
}) {
  const t = STATUS_TONE[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide ${t.text}`}>
      <span className="relative flex h-1.5 w-1.5">
        {pulse && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${t.dot}`} />}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${t.dot}`} />
      </span>
      {children}
    </span>
  );
}

const STAT_ACCENT: Record<Accent, { bar: string; val: string }> = {
  teal: { bar: "from-brand to-brand-light", val: "text-brand-dark" },
  gold: { bar: "from-gold to-gold-light", val: "text-gold" },
  coral: { bar: "from-coral to-[#ffb3aa]", val: "text-coral" },
  purple: { bar: "from-purple to-[#b3a4ff]", val: "text-purple" },
  sky: { bar: "from-sky to-[#a6d8ff]", val: "text-sky" },
  navy: { bar: "from-navy to-navy-light", val: "text-navy" },
};

export function Stat({
  label,
  value,
  hint,
  accent = "teal",
  href,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  accent?: Accent;
  href?: string;
}) {
  const a = STAT_ACCENT[accent] ?? STAT_ACCENT.teal;
  const inner = (
    <>
      <div className={`h-1.5 bg-gradient-to-r ${a.bar}`} />
      <div className="p-5">
        <div className="flex items-center justify-between text-sm text-ss-muted">
          <span>{label}</span>
          {href && <span className={`text-xs font-semibold ${a.val} transition group-hover:translate-x-0.5`}>View →</span>}
        </div>
        <div className={`mt-1 text-3xl font-bold tracking-tight ${a.val} [text-shadow:0_0_22px_var(--ss-primary-glow)]`}>{value}</div>
        {hint && <div className="mt-1 text-xs text-ss-muted">{hint}</div>}
      </div>
    </>
  );
  const cls = "ss-card-neon group block overflow-hidden rounded-2xl border border-ss-border bg-ss-surface shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-300 hover:-translate-y-0.5 hover:border-ss-tech hover:shadow-[0_0_0_1px_var(--ss-tech-glow),0_22px_60px_-22px_var(--ss-tech-glow)]";
  return href ? (
    <Link href={href} className={cls}>{inner}</Link>
  ) : (
    <div className={cls}>{inner}</div>
  );
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  glow = false,
  ...props
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  /** Adds a diagonal sheen sweep on hover -- the same hightech touch used on
      the homepage's hero CTAs. Opt-in and off by default. */
  glow?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm hover:shadow-md hover:brightness-110 focus-visible:ring-brand/40",
    secondary: "bg-ss-primary-soft text-ss-text hover:bg-ss-primary-soft-strong focus-visible:ring-ss-primary",
    ghost: "border border-ss-border text-ss-text hover:border-brand hover:bg-brand/5 hover:text-brand-dark focus-visible:ring-brand/30",
    danger: "bg-ss-danger text-white hover:brightness-110 focus-visible:ring-ss-danger",
  }[variant];
  const sizes = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-5 py-2.5 text-base",
  }[size];
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={`group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-lg font-medium transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ${sizes} ${styles} ${props.className || ""}`}
    >
      {loading && (
        <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      )}
      <span className="relative z-10 inline-flex items-center gap-2">{children}</span>
      {glow && (
        <span className="pointer-events-none absolute inset-0 -translate-x-full skew-x-[-20deg] bg-white/25 opacity-0 transition-all duration-700 group-hover:translate-x-full group-hover:opacity-100" />
      )}
    </button>
  );
}

const BAND_COLORS: Record<string, string> = {
  Strong: "bg-green-100 text-green-800",
  Good: "bg-teal-100 text-teal-800",
  Possible: "bg-yellow-100 text-yellow-800",
  Weak: "bg-orange-100 text-orange-800",
  Reject: "bg-gray-100 text-gray-600",
  APPLY: "bg-green-100 text-green-800",
  REVIEW: "bg-yellow-100 text-yellow-800",
  DO_NOT_APPLY: "bg-gray-100 text-gray-600",
  ACTIVE: "bg-green-100 text-green-800",
  TRIAL: "bg-sky/15 text-sky",
  PAST_DUE: "bg-orange-100 text-orange-800",
  CANCELLED: "bg-gray-100 text-gray-600",
  EXPIRED: "bg-gray-100 text-gray-600",
};

export function Badge({ children }: { children: string }) {
  const cls = BAND_COLORS[children] || "bg-brand/10 text-brand-dark";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold tracking-tight ${cls}`}>{children}</span>;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline justify-between">
        <span className="text-sm font-medium text-ss-text">{label}</span>
        {hint && <span className="text-xs text-ss-muted">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

const FIELD_BASE =
  "w-full rounded-lg border border-ss-border bg-ss-surface px-3.5 py-2.5 text-sm text-ss-text placeholder:text-ss-muted shadow-sm transition-all duration-150 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:opacity-60";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${FIELD_BASE} ${props.className || ""}`} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${FIELD_BASE} resize-y ${props.className || ""}`} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${FIELD_BASE} ${props.className || ""}`} />;
}

const ALERT_STYLE: Record<"info" | "error" | "success", { cls: string; icon: ReactNode }> = {
  info: {
    cls: "bg-sky/5 text-navy border-sky/25",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 flex-none text-sky" aria-hidden="true">
        <path fillRule="evenodd" d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM9 9a1 1 0 012 0v4a1 1 0 11-2 0V9zm1-4a1.25 1.25 0 100 2.5A1.25 1.25 0 0010 5z" clipRule="evenodd" />
      </svg>
    ),
  },
  error: {
    cls: "bg-coral/5 text-[#8a2c22] border-coral/25",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 flex-none text-coral" aria-hidden="true">
        <path fillRule="evenodd" d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
      </svg>
    ),
  },
  success: {
    cls: "bg-brand/5 text-brand-dark border-brand/25",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 flex-none text-brand" aria-hidden="true">
        <path fillRule="evenodd" d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zm-11.03-.53a.75.75 0 10-1.06 1.06l2 2a.75.75 0 001.137-.089l4-5.5a.75.75 0 10-1.214-.882l-3.483 4.79-1.374-1.375z" clipRule="evenodd" />
      </svg>
    ),
  },
};

export function Alert({ kind = "info", children }: { kind?: "info" | "error" | "success"; children: ReactNode }) {
  const { cls, icon } = ALERT_STYLE[kind];
  return (
    <div className={`flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm leading-relaxed ${cls}`}>
      {icon}
      <div>{children}</div>
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-10 text-sm text-ss-muted">
      <svg className="h-4 w-4 animate-spin text-brand" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
      <span>{label}</span>
    </div>
  );
}

/** Skeleton block for content that is loading — pairs nicely with card-shaped
 * placeholders. A gentle left-to-right shimmer (not a flat pulse) reads as
 * "content is arriving" rather than "something is broken"; respects
 * prefers-reduced-motion via the existing .animate-shimmer rule. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-shimmer rounded-lg bg-ss-border ${className}`}
      style={{ backgroundImage: "linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)" }}
    />
  );
}

/** A meaningful, on-brand empty state (brief section 21) -- never a generic
 * sad illustration. Pass an icon (an emoji or small inline SVG is fine). */
export function EmptyState({
  icon,
  title,
  message,
  action,
}: {
  icon?: ReactNode;
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-ss-border bg-ss-glass px-6 py-12 text-center">
      {icon && <div className="text-3xl">{icon}</div>}
      <div className="text-sm font-bold uppercase tracking-wide text-ss-text">{title}</div>
      {message && <p className="max-w-sm text-sm text-ss-muted">{message}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/** A calm, non-technical error state (brief section 22) -- no stack traces
 * or raw messages for normal users; pass the real error via `detail` only
 * if the caller wants it shown in small print underneath. */
export function ErrorState({
  title = "Something interrupted the connection",
  message = "We couldn't retrieve this right now.",
  detail,
  action,
}: {
  title?: string;
  message?: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-ss-danger-soft-border bg-ss-danger-soft px-6 py-10 text-center">
      <div className="text-2xl" aria-hidden="true">⚠</div>
      <div className="text-sm font-bold uppercase tracking-wide text-ss-danger">{title}</div>
      <p className="max-w-sm text-sm text-ss-muted">{message}</p>
      {detail && <p className="max-w-sm text-xs text-ss-muted">{detail}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
