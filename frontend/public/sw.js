// Sospana Sonke service worker: installable + works offline for browsing employers.
// Caches only public, non-personal data (static assets, pages, the employer directory).
// Also keeps the public jobs list (stale-while-revalidate) so /jobs works offline.
// Never caches messages, notifications, account, tips or any other personal API call.
const VERSION = "v8";
const STATIC = `ss-static-${VERSION}`;
const PAGES = `ss-pages-${VERSION}`;
const DATA = `ss-data-${VERSION}`;
const KEEP = [STATIC, PAGES, DATA];
const PUBLIC_API = /\/api\/v1\/(companies(\/trending)?|jobs)(\?|$)/;
// App shell: opened once on install so the site starts with no signal.
const SHELL = ["/offline.html", "/", "/jobs", "/login", "/register", "/sa-careers", "/offline-guide", "/manifest.webmanifest", "/icons/icon-192.png", "/logo-mark.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(PAGES)
      // One by one: a page that fails to load must not abort the whole install.
      .then((c) => Promise.all(SHELL.map((path) => c.add(path).catch(() => null))))
      .then(() => self.skipWaiting()),
  );
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

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // The game at /game/ has its own service worker (scope /game/); never touch it here.
  if (url.origin === self.location.origin && url.pathname.startsWith("/game/")) return;

  // Employer directory and jobs list (public): stale-while-revalidate so they open
  // instantly and offline. The page filters expired roles before showing them.
  if (PUBLIC_API.test(url.pathname + url.search)) {
    event.respondWith((async () => {
      const cached = await caches.match(req, { cacheName: DATA });
      const net = fetch(req).then((r) => put(DATA, req, r)).catch(() => null);
      if (cached) {
        event.waitUntil(net);
        return cached;
      }
      const fresh = await net;
      // An API error (database down) falls back to any earlier good copy of the list.
      if (fresh && fresh.ok) return fresh;
      const any = /\/jobs(\?|$)/.test(url.pathname) ? await caches.match(new Request(url.origin + url.pathname + "?limit=30"), { cacheName: DATA, ignoreSearch: true }) : null;
      return any || fresh || new Response("[]", { status: 503, headers: { "Content-Type": "application/json" } });
    })());
    return;
  }

  if (url.origin !== self.location.origin) return;

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
        return (await caches.match(req, { cacheName: PAGES })) ||
          (await caches.match(req, { cacheName: PAGES, ignoreSearch: true })) ||
          (await caches.match("/offline.html")) ||
          new Response("Offline", { status: 503 });
      }),
    );
  }
});
