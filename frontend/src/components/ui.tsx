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
  const interactiveCls = interactive ? "hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-8px_rgba(11,36,71,0.18)] hover:border-gray-300" : "";
  return (
    <div
      className={`rounded-2xl border border-gray-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-200 ${accentCls} ${interactiveCls} ${className}`}
    >
      {children}
    </div>
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
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{label}</span>
          {href && <span className={`text-xs font-semibold ${a.val} transition group-hover:translate-x-0.5`}>View →</span>}
        </div>
        <div className={`mt-1 text-3xl font-bold tracking-tight ${a.val}`}>{value}</div>
        {hint && <div className="mt-1 text-xs text-gray-400">{hint}</div>}
      </div>
    </>
  );
  const cls = "group block overflow-hidden rounded-2xl border border-gray-200/80 bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-8px_rgba(11,36,71,0.18)]";
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
  ...props
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm hover:shadow-md hover:brightness-110 focus-visible:ring-brand/40",
    secondary: "bg-navy/5 text-navy hover:bg-navy/10 focus-visible:ring-navy/30",
    ghost: "border border-gray-300 text-gray-700 hover:border-brand hover:bg-brand/5 hover:text-brand-dark focus-visible:ring-brand/30",
    danger: "bg-coral text-white hover:brightness-110 focus-visible:ring-coral/40",
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
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ${sizes} ${styles} ${props.className || ""}`}
    >
      {loading && (
        <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      )}
      {children}
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
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {hint && <span className="text-xs text-gray-400">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

const FIELD_BASE =
  "w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition-all duration-150 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400";

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
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 flex-none text-sky">
        <path fillRule="evenodd" d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM9 9a1 1 0 012 0v4a1 1 0 11-2 0V9zm1-4a1.25 1.25 0 100 2.5A1.25 1.25 0 0010 5z" clipRule="evenodd" />
      </svg>
    ),
  },
  error: {
    cls: "bg-coral/5 text-[#8a2c22] border-coral/25",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 flex-none text-coral">
        <path fillRule="evenodd" d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
      </svg>
    ),
  },
  success: {
    cls: "bg-brand/5 text-brand-dark border-brand/25",
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 flex-none text-brand">
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
    <div className="flex items-center justify-center gap-2.5 py-10 text-sm text-gray-400">
      <svg className="h-4 w-4 animate-spin text-brand" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
      <span>{label}</span>
    </div>
  );
}

/** Skeleton block for content that is loading — pairs nicely with card-shaped placeholders. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-gray-200/70 ${className}`} />;
}
