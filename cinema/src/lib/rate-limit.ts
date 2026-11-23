type Bucket = { count: number; reset: number };

const buckets = new Map<string, Bucket>();

export function rateLimit(key: string, limit: number, windowMs: number, now = Date.now()): { ok: boolean; retryAfterSeconds: number } {
  const current = buckets.get(key);
  if (!current || current.reset <= now) {
    buckets.set(key, { count: 1, reset: now + windowMs });
    return { ok: true, retryAfterSeconds: 0 };
  }
  if (current.count >= limit) {
    return { ok: false, retryAfterSeconds: Math.max(1, Math.ceil((current.reset - now) / 1000)) };
  }
  current.count += 1;
  return { ok: true, retryAfterSeconds: 0 };
}

export function resetRateLimits(): void {
  buckets.clear();
}
