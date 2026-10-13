// Sospana Sonke service worker: installable + works offline for browsing employers.
// Caches only public, non-personal data (static assets, pages, the employer directory).
// Never caches messages, notifications, account, tips or any other personal API call.
const VERSION = "v4";
const STATIC = `ss-static-${VERSION}`;
const PAGES = `ss-pages-${VERSION}`;
const DATA = `ss-data-${VERSION}`;
const KEEP = [STATIC, PAGES, DATA];
const PUBLIC_API = /\/api\/v1\/companies(\/trending)?(\?|$)/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(PAGES).then((c) => c.addAll(["/offline.html"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("ss-") && !KEEP.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function put(name, req, res) {
  if (res && res.ok) {
    const c = await caches.open(name);
    c.put(req, res.clone());
  }
  return res;
}

const ROLE_PAGE = /^\/jobs\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

self.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.type !== "cache-role" || typeof data.url !== "string" || !ROLE_PAGE.test(data.url)) return;
  event.waitUntil(caches.open(PAGES).then((cache) => cache.add(data.url)));
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Employer directory (public): stale-while-revalidate so it opens instantly and offline.
  if (PUBLIC_API.test(url.pathname + url.search)) {
    event.respondWith((async () => {
      const cached = await caches.match(req, { cacheName: DATA });
      const net = fetch(req).then((r) => put(DATA, req, r)).catch(() => null);
      return cached || (await net) || new Response("[]", { status: 503, headers: { "Content-Type": "application/json" } });
    })());
    return;
  }

  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  // Built assets and icons: cache-first (hashed filenames never change).
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith((async () => {
      const cached = await caches.match(req, { cacheName: STATIC });
      return cached || fetch(req).then((r) => put(STATIC, req, r));
    })());
    return;
  }

  // Pages: network-first, fall back to the last copy, then the offline page.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).then((r) => put(PAGES, req, r)).catch(async () => {
        return (await caches.match(req, { cacheName: PAGES })) || (await caches.match("/offline.html")) ||
          new Response("Offline", { status: 503 });
      }),
    );
  }
});
