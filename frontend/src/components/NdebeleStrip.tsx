"use client";

// Ndebele-art-inspired decorative border. No page mounts this any more: the
// band fought the photographic layout. Kept so the pattern can return as a
// single accent without being redrawn. Logo, gold, and navy carry the brand.
//
// `palette` picks which row set to use -- "classic" is the original 3-row
// strip (red/gold, navy/sky, green/orange); "vivid" is a wider 5-row strip
// for sections that want a bolder, more colourful accent.
const PALETTES: Record<string, { bg: string; tri: string }[]> = {
  classic: [
    { bg: "#e4322b", tri: "#FCC033" }, // red / gold
    { bg: "#07284C", tri: "#1184F0" }, // navy / sky
    { bg: "#269958", tri: "#ff7a1a" }, // green / sun
  ],
  vivid: [
    { bg: "#e4322b", tri: "#FCC033" }, // red / gold
    { bg: "#FCC033", tri: "#07284C" }, // gold / navy
    { bg: "#1184F0", tri: "#ffffff" }, // sky / white
    { bg: "#269958", tri: "#ff7a1a" }, // green / sun
    { bg: "#ff7a1a", tri: "#e4322b" }, // sun / red
  ],
};

export function NdebeleStrip({
  id,
  flip = false,
  className = "",
  palette = "classic",
  glow = false,
}: {
  id: string;
  flip?: boolean;
  className?: string;
  palette?: "classic" | "vivid";
  /** Adds a slow tri-colour shimmer sweep across the strip -- an opt-in
      hightech accent, off by default so existing callers are unaffected. */
  glow?: boolean;
}) {
  const base = PALETTES[palette] || PALETTES.classic;
  const rows = flip ? [...base].reverse() : base;
  return (
    <div className={`relative flex flex-col ${className}`} aria-hidden="true">
      {rows.map((row, i) => (
        <svg key={i} viewBox="0 0 200 18" preserveAspectRatio="none" className="block h-4 w-full">
          <defs>
            <pattern id={`${id}-tri-${i}`} width="18" height="18" patternUnits="userSpaceOnUse">
              <rect width="18" height="18" fill={row.bg} />
              <polygon
                points={flip ? "0,18 9,0 18,18" : "0,0 9,18 18,0"}
                fill={row.tri}
                stroke="#161616"
                strokeWidth="1"
                strokeLinejoin="round"
              />
            </pattern>
          </defs>
          <rect width="200" height="18" fill={`url(#${id}-tri-${i})`} />
        </svg>
      ))}
      {glow && (
        <div
          className="pointer-events-none absolute inset-0 animate-shimmer opacity-60"
          style={{ backgroundImage: "linear-gradient(100deg,transparent 30%,rgba(255,255,255,0.65) 50%,transparent 70%)" }}
        />
      )}
    </div>
  );
}
