"use client";

import { useEffect, type CSSProperties, type ReactNode } from "react";
import { recordOutboundClick } from "@/lib/usageSignal";

/**
 * One listener for server-rendered source links. A list page can print dozens
 * of them without hydrating a component on every card.
 */
export function OutboundClickListener() {
  useEffect(() => {
    function onClick(event: MouseEvent) {
      const node = event.target;
      if (!(node instanceof Element)) return;
      const link = node.closest("a[data-count-target]");
      if (!link) return;
      const kind = link.getAttribute("data-count-target");
      const id = link.getAttribute("data-count-id") || "";
      if (kind !== "employer" && kind !== "vacancy") return;
      recordOutboundClick(kind, id);
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);
  return null;
}

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
