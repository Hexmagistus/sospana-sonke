"use client";

import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from "react";
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
}: {
  children: ReactNode;
  className?: string;
  accent?: Accent;
}) {
  const accentCls = accent ? `border-l-4 ${ACCENT_LEFT[accent]}` : "";
  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition ${accentCls} ${className}`}
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
          {href && <span className={`text-xs font-semibold ${a.val}`}>View →</span>}
        </div>
        <div className={`mt-1 text-3xl font-bold ${a.val}`}>{value}</div>
        {hint && <div className="mt-1 text-xs text-gray-400">{hint}</div>}
      </div>
    </>
  );
  const cls = "block overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md";
  return href ? (
    <Link href={href} className={cls}>{inner}</Link>
  ) : (
    <div className={cls}>{inner}</div>
  );
}

export function Button({
  children,
  variant = "primary",
  ...props
}: { children: ReactNode; variant?: "primary" | "ghost" | "danger" } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-gradient-to-r from-brand to-brand-dark text-white shadow-sm hover:shadow-md hover:brightness-110",
    ghost: "border border-gray-300 text-gray-700 hover:border-brand hover:bg-brand/5 hover:text-brand-dark",
    danger: "bg-coral text-white hover:brightness-110",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${styles} ${props.className || ""}`}
    >
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
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{children}</span>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      {children}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand ${props.className || ""}`}
    />
  );
}

export function Alert({ kind = "info", children }: { kind?: "info" | "error" | "success"; children: ReactNode }) {
  const cls = {
    info: "bg-blue-50 text-blue-800 border-blue-200",
    error: "bg-red-50 text-red-800 border-red-200",
    success: "bg-green-50 text-green-800 border-green-200",
  }[kind];
  return <div className={`rounded-lg border px-4 py-3 text-sm ${cls}`}>{children}</div>;
}

export function Spinner() {
  return <div className="animate-pulse text-sm text-brand">Loading…</div>;
}
