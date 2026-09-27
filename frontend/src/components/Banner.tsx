"use client";

import Image from "next/image";
import { ReactNode } from "react";

type Variant = "dashboard" | "companies" | "tailor" | "jobs";

const PHOTO: Record<Variant, { src: string; position: string }> = {
  dashboard: { src: "/photos/workplace.jpg", position: "center 22%" },
  companies: { src: "/photos/cape-town-waterfront.jpg", position: "center 40%" },
  tailor: { src: "/photos/professional.jpg", position: "center 18%" },
  jobs: { src: "/photos/nairobi.jpg", position: "center" },
};

export function Banner({
  variant,
  eyebrow,
  title,
  subtitle,
  children,
}: {
  variant: Variant;
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  children?: ReactNode;
}) {
  const photo = PHOTO[variant];
  return (
    <div className="banner relative isolate overflow-hidden rounded-[1.6rem] text-white shadow-[0_24px_60px_-28px_rgba(7,21,40,0.75)] ring-1 ring-white/15">
      <Image
        src={photo.src}
        alt=""
        fill
        priority={variant === "dashboard" || variant === "companies"}
        sizes="(max-width: 768px) 100vw, 1100px"
        className="object-cover"
        style={{ objectPosition: photo.position }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(105deg, rgba(7,21,40,0.92) 0%, rgba(11,31,58,0.78) 46%, rgba(11,31,58,0.42) 100%)",
        }}
      />
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.16] mix-blend-overlay" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold/80 to-transparent" />
      <div className="pointer-events-none absolute -right-8 -top-16 h-48 w-48 rounded-full bg-gold/25 blur-3xl" />
      <div className="relative flex items-center justify-between gap-6 p-6 sm:p-8">
        <div className="max-w-xl">
          {eyebrow && (
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-gold">{eyebrow}</p>
          )}
          <h1 className="text-2xl font-extrabold leading-tight sm:text-3xl">{title}</h1>
          {subtitle && <p className="mt-2 max-w-lg text-sm leading-relaxed text-blue-100 sm:text-base">{subtitle}</p>}
          {children && <div className="mt-4">{children}</div>}
        </div>
        <div className="hidden h-28 w-28 shrink-0 overflow-hidden rounded-2xl shadow-lg ring-1 ring-white/30 sm:block">
          <Image src={photo.src} alt="" width={224} height={224} className="h-full w-full object-cover" style={{ objectPosition: photo.position }} />
        </div>
      </div>
    </div>
  );
}
