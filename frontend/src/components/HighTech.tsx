"use client";

// Shared Afro-futurist / hightech accents -- the same visual language used on
// the homepage redesign (faint circuit-mesh overlays, a rotating tri-colour
// holo-frame, a pulsing logo glow), pulled out here so any public page can
// opt into it without duplicating the homepage's page-local components.

import { ReactNode } from "react";

/** Faint circuit-board / network-mesh overlay. `stroke`/`dotColor` let it
    adapt to a dark panel (white lines) or a light page (dark, low-opacity
    lines) -- the "connecting talent to opportunity" sensor-grid motif. */
export function CircuitOverlay({
  className = "",
  opacity = 0.14,
  stroke = "#ffffff",
  dotColor = "#f5b301",
}: {
  className?: string;
  opacity?: number;
  stroke?: string;
  dotColor?: string;
}) {
  const nodes: [number, number][] = [
    [30, 26], [130, 14], [220, 42], [66, 84], [182, 96], [274, 62],
    [18, 132], [116, 146], [242, 140], [322, 34], [332, 114], [78, 20],
  ];
  const edges: [number, number][] = [
    [0, 1], [1, 2], [1, 3], [3, 4], [4, 5], [3, 6], [6, 7], [7, 8],
    [2, 9], [9, 10], [4, 10], [0, 11], [11, 1],
  ];
  return (
    <svg
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
      viewBox="0 0 360 180"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      style={{ opacity }}
    >
      {edges.map(([a, b], i) => (
        <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} stroke={stroke} strokeWidth="0.6" />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 2.6 : 1.4} fill={i % 3 === 0 ? dotColor : stroke} />
      ))}
    </svg>
  );
}

/** Slow-rotating tri-colour holo-frame -- wraps a panel in a thin conic-gradient
    ring (gold -> green -> red -> sky, the platform's palette) for a hightech,
    "powered on" edge-glow. The wrapped child supplies its own background. */
export function GlowFrame({
  children,
  className = "",
  colors = ["#f5b301", "#1a9e5f", "#e4322b", "#2f9bf6", "#f5b301"],
  ringClassName = "rounded-2xl",
}: {
  children: ReactNode;
  className?: string;
  colors?: string[];
  ringClassName?: string;
}) {
  return (
    <div className={`relative p-[2px] ${ringClassName} ${className}`}>
      <div
        className={`absolute inset-0 animate-spin-slow ${ringClassName}`}
        style={{ background: `conic-gradient(from 0deg, ${colors.join(",")})`, opacity: 0.8 }}
        aria-hidden="true"
      />
      <div className={`relative ${ringClassName}`}>{children}</div>
    </div>
  );
}

/** Soft pulsing glow ring behind a logo mark, matching the homepage header. */
export function LogoGlow({
  children,
  color = "#f5b301",
  className = "",
}: {
  children: ReactNode;
  color?: string;
  className?: string;
}) {
  return (
    <div className={`relative inline-block ${className}`}>
      <div
        className="absolute inset-0 -z-10 animate-pulse-glow rounded-2xl blur-md"
        style={{ background: color, opacity: 0.45 }}
        aria-hidden="true"
      />
      {children}
    </div>
  );
}
