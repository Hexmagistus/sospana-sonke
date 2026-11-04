/** Small inline SVG charts for the stat cards. Each is labelled for screen readers. */

export function MiniLine({ points, color, label }: { points: { label: string; value: number }[]; color: string; label: string }) {
  const w = 120, h = 48, pad = 6;
  const vals = points.map((p) => p.value);
  const lo = Math.min(...vals) - 0.5, hi = Math.max(...vals) + 0.5;
  const xy = points.map((p, i) => [pad + (i * (w - 2 * pad)) / Math.max(1, points.length - 1), h - pad - ((p.value - lo) / (hi - lo)) * (h - 2 * pad)]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");
  const area = `${line}L${xy[xy.length - 1][0].toFixed(1)},${h}L${xy[0][0].toFixed(1)},${h}Z`;
  const id = `g-${color.slice(1)}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-12 w-28" role="img" aria-label={label}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {xy.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="3" fill="#fff" stroke={color} strokeWidth="2" />)}
    </svg>
  );
}

export function MiniBars({ bars, color, label }: { bars: { label: string; value: number }[]; color: string; label: string }) {
  const w = 120, h = 48, gap = 10;
  const bw = (w - gap * (bars.length + 1)) / bars.length;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-12 w-28" role="img" aria-label={label}>
      {bars.map((b, i) => {
        const bh = (b.value / 100) * (h - 4);
        return <rect key={b.label} x={gap + i * (bw + gap)} y={h - bh} width={bw} height={bh} rx="4" fill={color} opacity={0.45 + (0.55 * (i + 1)) / bars.length} />;
      })}
    </svg>
  );
}

export function MiniStack({ parts, label }: { parts: { label: string; value: number; color: string }[]; label: string }) {
  let x = 0;
  return (
    <svg viewBox="0 0 120 48" className="h-12 w-28" role="img" aria-label={label}>
      <defs><clipPath id="ss-stack-clip"><rect x="0" y="18" width="120" height="14" rx="7" /></clipPath></defs>
      <rect x="0" y="18" width="120" height="14" rx="7" fill="#F1EADB" />
      <g clipPath="url(#ss-stack-clip)">
      {parts.map((p) => {
        const wv = (p.value / 100) * 120;
        const r = <rect key={p.label} x={x} y="18" width={wv} height="14" fill={p.color} />;
        x += wv;
        return r;
      })}
      </g>
    </svg>
  );
}
