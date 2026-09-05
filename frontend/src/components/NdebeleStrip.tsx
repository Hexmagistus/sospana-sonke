"use client";

// Ndebele-art-inspired decorative border bands (bold black-outlined geometric
// triangles in bright alternating colors, echoing the mural/beadwork tradition
// of the amaNdebele). Shared so any page can frame a card/section with it.
//
// `palette` picks which row set to use -- "classic" is the original 3-row
// strip (red/gold, navy/sky, green/orange); "vivid" is a wider 5-row strip
// for sections that want a bolder, more colourful accent.
const PALETTES: Record<string, { bg: string; tri: string }[]> = {
  classic: [
    { bg: "#e4322b", tri: "#f5b301" }, // red / gold
    { bg: "#0b1f3a", tri: "#2f9bf6" }, // navy / sky
    { bg: "#1a9e5f", tri: "#ff7a1a" }, // green / sun
  ],
  vivid: [
    { bg: "#e4322b", tri: "#f5b301" }, // red / gold
    { bg: "#f5b301", tri: "#0b1f3a" }, // gold / navy
    { bg: "#2f9bf6", tri: "#ffffff" }, // sky / white
    { bg: "#1a9e5f", tri: "#ff7a1a" }, // green / sun
    { bg: "#ff7a1a", tri: "#e4322b" }, // sun / red
  ],
};

export function NdebeleStrip({
  id,
  flip = false,
  className = "",
  palette = "classic",
}: {
  id: string;
  flip?: boolean;
  className?: string;
  palette?: "classic" | "vivid";
}) {
  const base = PALETTES[palette] || PALETTES.classic;
  const rows = flip ? [...base].reverse() : base;
  return (
    <div className={`flex flex-col ${className}`} aria-hidden="true">
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
    </div>
  );
}
