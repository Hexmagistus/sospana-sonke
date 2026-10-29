/* Gauteng Hustle Run - service worker (v3.2)
   * precache (install): `core` files must all succeed; `eager` files (hero + people sprites, icons, first 3 area plates ...) best-effort
   * runtime: cache-first for every same-origin GET (so the game opens instantly, also with NO network);
     code/pages are refreshed in the background (stale-while-revalidate); everything else is stored the first time it is seen
     (that is how the 34 WebP plates get cached lazily as the visitor runs through the areas)
   * navigation fallback: offline + page not cached -> cached index.html
   * versioned cache name: ghr-<BUILD>; old caches are deleted on activate.  BUILD is rewritten by tools/build_pwa.py. */
const BUILD = "3.2-3b53d3c1d4";
const CACHE = "ghr-" + BUILD;
const CODE_RE = /\.(?:html|js|css|json|webmanifest)$/i;

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const res = await fetch("precache.json", { cache: "reload" });
    const list = await res.clone().json();
    await cache.addAll(list.core.map((u) => new Request(u, { cache: "reload" })));
    await cache.put("precache.json", res);
    await Promise.allSettled(list.eager.map((u) => cache.add(new Request(u, { cache: "reload" }))));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.indexOf("ghr-") === 0 && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

async function refresh(cache, req) {
  try {
    const net = await fetch(req, { cache: "no-cache" });
    if (net && net.ok && net.type === "basic") await cache.put(req, net);
  } catch (e) { /* offline: keep what we have */ }
}

const OFFLINE_HTML = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline</title>' +
  '<body style="margin:0;background:#1a140e;color:#ffd23f;font:700 18px system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center">' +
  '<div>📴 You are offline and the game has not been saved on this device yet.<br><small style="color:#fff">Connect once and open Gauteng Hustle Run - after that it plays with no internet.</small></div>';

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (/\/sw\.js$/.test(url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const nav = req.mode === "navigate";
    let hit = await cache.match(req, { ignoreSearch: true });
    if (!hit && nav) hit = await cache.match("index.html");
    if (hit) {
      if (nav || CODE_RE.test(url.pathname)) event.waitUntil(refresh(cache, req));
      return hit;
    }
    try {
      const net = await fetch(req);
      if (net && net.ok && net.type === "basic") cache.put(req, net.clone());
      return net;
    } catch (e) {
      if (nav) return new Response(OFFLINE_HTML, { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } });
      return new Response("", { status: 504, statusText: "offline" });
    }
  })());
});
