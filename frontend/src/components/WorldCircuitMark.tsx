/**
 * Code-drawn brand mark. Gold circuits on navy.
 * Africa is drawn largest because the platform started in the SADC region.
 * Europe and Oceania are marked because they are on the directory now.
 * The faint outlines are room for later continents. No map tiles, no photos of people.
 */
export default function WorldCircuitMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 320 420"
      role="img"
      aria-label="Born in SADC, built for the world. Africa, Europe and Oceania on a gold circuit."
      className={className}
    >
      <defs>
        <linearGradient id="ss-navy" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#071528" />
          <stop offset="1" stopColor="#0b1f3a" />
        </linearGradient>
        <linearGradient id="ss-gold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffcf5a" />
          <stop offset="1" stopColor="#f5b301" />
        </linearGradient>
      </defs>
      <rect width="320" height="420" rx="28" fill="url(#ss-navy)" />
      <g fill="none" stroke="#f5b301" strokeWidth="1.2" opacity="0.55">
        <path d="M24 70 H120 V40 H200" />
        <path d="M40 150 H90 V210 H40" />
        <path d="M230 80 H290 V140 H250" />
        <path d="M200 250 H290 V320" />
        <path d="M30 300 H80 V360 H150" />
        <circle cx="120" cy="70" r="3" fill="#f5b301" stroke="none" />
        <circle cx="200" cy="40" r="3" fill="#f5b301" stroke="none" />
        <circle cx="90" cy="210" r="3" fill="#f5b301" stroke="none" />
        <circle cx="290" cy="140" r="3" fill="#f5b301" stroke="none" />
        <circle cx="200" cy="250" r="3" fill="#f5b301" stroke="none" />
        <circle cx="150" cy="360" r="3" fill="#f5b301" stroke="none" />
      </g>
      {/* Later continents, drawn faint on purpose. */}
      <g fill="none" stroke="#9fb4d0" strokeWidth="1.2" strokeDasharray="3 3" opacity="0.45">
        <path d="M48 118 C40 100 52 78 70 82 C86 70 100 90 92 108 C78 122 56 128 48 118 Z" />
        <path d="M248 168 C270 150 292 168 286 190 C274 210 250 200 248 168 Z" />
      </g>
      {/* Europe */}
      <path
        d="M168 78 C182 62 210 66 214 86 C226 90 222 108 206 112 C190 124 168 112 164 96 C156 88 158 80 168 78 Z"
        fill="#5fe0d0"
        opacity="0.9"
      />
      {/* Oceania */}
      <path
        d="M236 196 C258 186 278 200 274 218 C266 232 244 228 236 214 C228 206 226 198 236 196 Z"
        fill="#2f9bf6"
        opacity="0.9"
      />
      <circle cx="286" cy="214" r="4" fill="#5fe0d0" />
      {/* Africa, largest, with a gold SADC mark in the south. */}
      <path
        d="M132 118 C156 104 188 112 198 140 C214 160 210 200 196 236 C188 268 176 300 158 312 C140 300 128 270 122 236 C108 200 104 156 118 132 C122 122 126 118 132 118 Z"
        fill="url(#ss-gold)"
      />
      <path d="M146 248 H176 L161 270 Z" fill="#0b1f3a" />
      <text x="160" y="292" textAnchor="middle" fill="#071528" fontSize="11" fontWeight="700">
        SADC
      </text>
      <text x="188" y="74" fill="#e8f7f5" fontSize="11" fontWeight="600">Europe</text>
      <text x="228" y="186" fill="#e8f4ff" fontSize="11" fontWeight="600">Oceania</text>
      <text x="160" y="168" textAnchor="middle" fill="#3a2b00" fontSize="13" fontWeight="700">Africa</text>
      {/* Ndebele-inspired geometric strip. Original triangles, not a copied textile. */}
      <g>
        <rect x="24" y="368" width="272" height="28" rx="6" fill="#071528" />
        {Array.from({ length: 12 }).map((_, i) => (
          <polygon
            key={i}
            points={`${32 + i * 22},390 ${43 + i * 22},372 ${54 + i * 22},390`}
            fill={i % 2 === 0 ? "#f5b301" : "#ffffff"}
          />
        ))}
      </g>
      <text x="160" y="348" textAnchor="middle" fill="#ffcf5a" fontSize="13" fontWeight="700">
        Born in SADC, built for the world
      </text>
    </svg>
  );
}
