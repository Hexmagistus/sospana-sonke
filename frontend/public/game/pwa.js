/* Gauteng Hustle Run - offline / install layer (v3.2)
   - registers sw.js (only on http/https, never inside Capacitor / file:)
   - 'Offline mode' badge, 'Download for offline play' button with progress,
     'Install app' button (beforeinstallprompt), fullscreen button
   Everything uses RELATIVE urls so the game works from any sub-folder (e.g. /game/). */
(function () {
  "use strict";
  var el = function (id) { return document.getElementById(id); };
  var isNative = !!window.Capacitor || /^(capacitor|ionic|file|app):/.test(location.protocol);
  var httpOK = /^https?:$/.test(location.protocol);
  var swOK = httpOK && !isNative && "serviceWorker" in navigator && "caches" in window && !/[?&]nosw\b/.test(location.search);
  var standalone = (window.matchMedia && (matchMedia("(display-mode: standalone)").matches || matchMedia("(display-mode: fullscreen)").matches)) || window.navigator.standalone === true;
  var state = { list: null, cacheName: null, busy: false, total: 0, done: 0 };
  window.__ghrPwa = state;

  /* ---------- offline badge ---------- */
  function updateOnline() {
    var b = el("offlineBadge"); if (b) b.classList.toggle("hidden", navigator.onLine !== false);
    refreshStatus();
  }
  window.addEventListener("online", updateOnline);
  window.addEventListener("offline", updateOnline);

  /* ---------- helpers ---------- */
  function setStatus(html, warn) {
    var s = el("offlineStatus"); if (!s) return;
    if (!html) { s.classList.add("hidden"); s.innerHTML = ""; return; }
    s.classList.remove("hidden"); s.classList.toggle("warn", !!warn); s.innerHTML = html;
  }
  function mb(n) { return (n / 1048576).toFixed(1) + " MB"; }
  function loadList() {
    if (state.list) return Promise.resolve(state.list);
    return fetch("precache.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (j) { state.list = j; return j; });
  }
  function openCache() {
    return loadList().then(function (list) {
      return caches.keys().then(function (keys) {
        var mine = "ghr-" + list.build;
        state.cacheName = keys.indexOf(mine) >= 0 || !keys.some(function (k) { return k.indexOf("ghr-") === 0; }) ? mine : keys.filter(function (k) { return k.indexOf("ghr-") === 0; }).sort().pop();
        return caches.open(state.cacheName);
      });
    });
  }
  function allUrls(list) { return list.core.concat(list.eager, list.rest).map(function (u) { return u.url || u; }); }
  function sizeOf(list, url) { var f = list.sizes && list.sizes[url]; return f || 0; }

  function countCached() {
    return openCache().then(function (cache) {
      var list = state.list, urls = allUrls(list);
      return Promise.all(urls.map(function (u) { return cache.match(u, { ignoreSearch: true }).then(function (r) { return !!r; }); })).then(function (flags) {
        var n = flags.filter(Boolean).length, bytes = 0;
        urls.forEach(function (u, i) { if (flags[i]) bytes += sizeOf(list, u); });
        return { cached: n, total: urls.length, bytes: bytes, missing: urls.filter(function (u, i) { return !flags[i]; }) };
      });
    });
  }
  // fetch + store a list of urls with a small worker pool; skips what is already cached
  function cacheUrls(urls, concurrency, onProgress) {
    return openCache().then(function (cache) {
      var queue = urls.slice(), done = 0, fail = 0, total = urls.length;
      function one() {
        var u = queue.shift(); if (!u) return Promise.resolve();
        return cache.match(u, { ignoreSearch: true }).then(function (hit) {
          if (hit) return;
          return fetch(u, { cache: "reload" }).then(function (r) { if (r.ok) return cache.put(u, r); fail++; }).catch(function () { fail++; });
        }).then(function () { done++; if (onProgress) onProgress(done, total); return one(); });
      }
      var workers = []; for (var i = 0; i < concurrency; i++) workers.push(one());
      return Promise.all(workers).then(function () { return { done: done, fail: fail, total: total }; });
    });
  }

  function refreshStatus() {
    if (!swOK || state.busy) return;
    countCached().then(function (c) {
      var b = el("offlineBtn");
      if (c.cached >= c.total - 0) {
        setStatus("✓ Ready for offline play (" + mb(c.bytes) + " saved on this device)");
        if (b) b.textContent = "✓ OFFLINE READY";
      } else if (navigator.onLine === false) {
        setStatus("Offline: " + c.cached + "/" + c.total + " files saved - some areas may look plain until you go online.", true);
      } else {
        setStatus("");
        if (b) b.textContent = "⬇ DOWNLOAD FOR OFFLINE PLAY";
      }
    }).catch(function () {});
  }

  function downloadAll() {
    if (state.busy) return;
    if (navigator.onLine === false) { setStatus("You are offline - connect once to download the game.", true); return; }
    state.busy = true;
    var b = el("offlineBtn"); if (b) b.disabled = true;
    loadList().then(function (list) {
      var urls = allUrls(list), total = urls.length;
      setStatus('Downloading… <span class="offline-progress"><i id="offBar"></i></span><span id="offTxt">0/' + total + "</span>");
      return cacheUrls(urls, 4, function (d, t) {
        var bar = el("offBar"), tx = el("offTxt"); if (bar) bar.style.width = Math.round(d / t * 100) + "%"; if (tx) tx.textContent = d + "/" + t;
      });
    }).then(function (r) {
      state.busy = false; if (b) b.disabled = false;
      if (r.fail) { setStatus("Saved " + (r.total - r.fail) + "/" + r.total + " files - " + r.fail + " could not be downloaded. Tap again to retry.", true); if (b) b.textContent = "⬇ RETRY OFFLINE DOWNLOAD"; }
      else { try { localStorage.setItem("ghr_offline_ready", state.list.build); } catch (e) {} refreshStatus(); }
    }).catch(function () { state.busy = false; if (b) b.disabled = false; setStatus("Download failed - check your connection and try again.", true); });
  }

  /* ---------- service worker ---------- */
  function boot() {
    updateOnline();
    var ob = el("offlineBtn");
    if (swOK) {
      navigator.serviceWorker.register("sw.js", { scope: "./" }).then(function () {
        if (ob) { ob.classList.remove("hidden"); ob.addEventListener("click", downloadAll); }
        refreshStatus();
        // first visit: make sure the essentials are stored, then quietly fetch the rest in the background
        if (navigator.onLine !== false) setTimeout(function () {
          var saveData = navigator.connection && navigator.connection.saveData;
          loadList().then(function (list) {
            var first = list.core.concat(list.eager);
            return cacheUrls(first, 3).then(function () { return saveData ? null : cacheUrls(list.rest, 2); });
          }).then(refreshStatus).catch(function () {});
        }, 3500);
      }).catch(function (e) { if (window.console) console.warn("service worker not registered", e); });
    }
    // install button
    var ib = el("installBtn"), deferred = null;
    window.addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; if (ib && !standalone && !isNative) ib.classList.remove("hidden"); });
    window.addEventListener("appinstalled", function () { deferred = null; if (ib) ib.classList.add("hidden"); setStatus("✓ Installed - look for it on your Home Screen."); });
    if (ib) ib.addEventListener("click", function () { if (!deferred) return; deferred.prompt(); deferred.userChoice.then(function () { deferred = null; ib.classList.add("hidden"); }); });
    var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    if (ios && !standalone && !isNative && el("iosHint")) el("iosHint").classList.remove("hidden");
    // fullscreen (handy inside an iframe with allow="fullscreen")
    var fb = el("fsBtn"), root = document.documentElement;
    var canFs = !isNative && !standalone && (document.fullscreenEnabled || document.webkitFullscreenEnabled);
    if (fb && canFs) {
      fb.classList.remove("hidden");
      fb.addEventListener("click", function () {
        var inFs = document.fullscreenElement || document.webkitFullscreenElement;
        if (inFs) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        else (root.requestFullscreen || root.webkitRequestFullscreen).call(root);
      });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
