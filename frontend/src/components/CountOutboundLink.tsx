"use client";

import type { CSSProperties, ReactNode } from "react";
import { recordOutboundClick } from "@/lib/usageSignal";

/**
 * An employer careers link or a role application link. The click adds one
 * anonymous daily count for that employer or role. The address is not stored.
 */
export default function CountOutboundLink({
  href,
  targetKind,
  targetId,
  className,
  style,
  children,
}: {
  href: string;
  targetKind: "employer" | "vacancy";
  targetId: string;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      style={style}
      onClick={() => recordOutboundClick(targetKind, targetId)}
    >
      {children}
    </a>
  );
}
