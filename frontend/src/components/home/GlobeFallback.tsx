/** Painted globe. It is in the first HTML, so a phone, a slow link, and no JavaScript still show it. */
export function GlobeFallback() {
  return (
    <svg viewBox="0 0 200 220" aria-hidden="true">
      <defs>
        <radialGradient id="ss-globe-body" cx="36%" cy="30%" r="72%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="20%" stopColor="#c5eefb" />
          <stop offset="52%" stopColor="#3d93bf" />
          <stop offset="100%" stopColor="#0c3d5c" />
        </radialGradient>
        <radialGradient id="ss-globe-shade" cx="70%" cy="72%" r="55%">
          <stop offset="0%" stopColor="rgba(7,17,31,0)" />
          <stop offset="100%" stopColor="rgba(7,17,31,0.55)" />
        </radialGradient>
        <linearGradient id="ss-globe-land" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7dffe8" />
          <stop offset="100%" stopColor="#0f766e" />
        </linearGradient>
        <clipPath id="ss-globe-clip">
          <circle cx="100" cy="96" r="68" />
        </clipPath>
      </defs>
      <ellipse cx="100" cy="188" rx="46" ry="8" fill="rgba(7,17,31,0.28)" />
      <circle cx="100" cy="96" r="72" fill="none" stroke="#b8fff3" strokeWidth="3" />
      <circle cx="100" cy="96" r="68" fill="url(#ss-globe-body)" />
      <g clipPath="url(#ss-globe-clip)">
        <path
          fill="url(#ss-globe-land)"
          d="M112 52c10 2 18 10 16 20 8 4 14 14 8 24 2 10-2 18-6 24-2 14-12 24-20 34-8-6-12-16-16-24-10 2-18-6-16-16-8-4-6-16 2-22 2-12 10-22 20-24 4-8 8-14 12-16z"
        />
        <path fill="rgba(255,255,255,0.28)" d="M78 70c16-18 42-16 54 2-20 4-36 2-54-2z" />
      </g>
      <circle cx="100" cy="96" r="68" fill="url(#ss-globe-shade)" />
      <ellipse cx="78" cy="70" rx="22" ry="12" fill="rgba(255,255,255,0.28)" />
    </svg>
  );
}
