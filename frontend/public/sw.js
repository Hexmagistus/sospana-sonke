// Minimal service worker for installability (network-first, no aggressive caching).
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (event) => {
  // Pass-through; a fetch handler is required for install prompts on some browsers.
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
