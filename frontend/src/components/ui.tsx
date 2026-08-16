"use client";

import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-gray-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-gray-400">{hint}</div>}
    </Card>
  );
}

export function Button({
  children,
  variant = "primary",
  ...props
}: { children: ReactNode; variant?: "primary" | "ghost" | "danger" } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-brand text-white hover:bg-brand-dark",
    ghost: "border border-gray-300 text-gray-700 hover:bg-gray-50",
    danger: "bg-red-600 text-white hover:bg-red-700",
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
};

export function Badge({ children }: { children: string }) {
  const cls = BAND_COLORS[children] || "bg-gray-100 text-gray-700";
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
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
  return <div className="animate-pulse text-sm text-gray-400">Loading…</div>;
}
