"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { DATA_SAVER_EVENT, isDataSaver, setDataSaver } from "@/lib/dataSaver";
import { useAuth } from "@/lib/auth";

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };
const DISMISS_KEY = "ss-install-dismissed";
const AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

/** Sign-in and registration fill the phone screen. The install card must not sit on them. */
export function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

function overlapsField(box: DOMRect): boolean {
  const fields = document.querySelectorAll("input, textarea, select");
  for (const field of fields) {
    const rect = field.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    const clear = box.right < rect.left || box.left > rect.right || box.bottom < rect.top || box.top > rect.bottom;
    if (!clear) return true;
  }
  return false;
}

/** Install-to-home-screen prompt, offline banner and the data-saver switch. */
export default function PwaExtras() {
  const pathname = usePathname() || "/";
  const { user } = useAuth();
  const onAuth = isAuthRoute(pathname);
  const bannerRef = useRef<HTMLDivElement>(null);
  const [installEv, setInstallEv] = useState<InstallEvent | null>(null);
  const [iosHint, setIosHint] = useState(false);
  const [offline, setOffline] = useState(false);
  const [saver, setSaver] = useState(false);
  const [typing, setTyping] = useState(false);
  const [dock, setDock] = useState<"bottom" | "top">("bottom");
  const [coversField, setCoversField] = useState(false);

  useEffect(() => {
    setOffline(!navigator.onLine);
    setSaver(isDataSaver());
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    const sync = () => setSaver(isDataSaver());
    const bip = (e: Event) => {
      e.preventDefault();
      try { if (window.localStorage.getItem(DISMISS_KEY)) return; } catch { /* ignore */ }
      setInstallEv(e as InstallEvent);
    };
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    window.addEventListener(DATA_SAVER_EVENT, sync);
    window.addEventListener("beforeinstallprompt", bip);

    const ua = navigator.userAgent;
    const isIos = /iphone|ipad|ipod/i.test(ua) && !/crios|fxios/i.test(ua);
    const standalone = window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone;
    let dismissed = false;
    try { dismissed = !!window.localStorage.getItem(DISMISS_KEY); } catch { /* ignore */ }
    if (isIos && !standalone && !dismissed) setIosHint(true);

    const onFocusIn = (event: FocusEvent) => {
      const target = event.target;
      if (target instanceof Element && target.closest("input, textarea, select")) setTyping(true);
    };
    const onFocusOut = () => {
      window.setTimeout(() => {
        const active = document.activeElement;
        const still = active instanceof Element && !!active.closest("input, textarea, select");
        setTyping(still);
      }, 0);
    };
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("focusout", onFocusOut);

    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
      window.removeEventListener(DATA_SAVER_EVENT, sync);
      window.removeEventListener("beforeinstallprompt", bip);
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("focusout", onFocusOut);
    };
  }, []);

  useEffect(() => {
    setDock("bottom");
    setCoversField(false);
  }, [pathname]);

  const offerInstall = Boolean(installEv || iosHint) && !onAuth && !typing && !coversField;

  useLayoutEffect(() => {
    const banner = bannerRef.current;
    if (!banner || !offerInstall) return;
    if (!overlapsField(banner.getBoundingClientRect())) return;
    if (dock === "bottom") setDock("top");
    else setCoversField(true);
  }, [offerInstall, dock]);

  function dismiss() {
    try { window.localStorage.setItem(DISMISS_KEY, "1"); } catch { /* ignore */ }
    setInstallEv(null);
    setIosHint(false);
  }

  async function install() {
    if (!installEv) return;
    await installEv.prompt();
    await installEv.userChoice.catch(() => null);
    setInstallEv(null);
  }

  return (
    <>
      {offline && (
        <div className="fixed inset-x-0 top-0 z-[70] bg-amber-500 px-3 py-1.5 text-center text-xs font-semibold text-black">
          📡 You&apos;re offline. Showing employers saved on this device.
        </div>
      )}

      {offerInstall && (
        <div
          ref={bannerRef}
          className={`fixed inset-x-3 z-[55] mx-auto max-w-sm rounded-2xl border border-ss-border bg-ss-surface p-4 shadow-xl md:bottom-4 md:left-auto md:right-4 md:top-auto md:mx-0 ${
            dock === "top" ? "top-16" : user ? "bottom-20" : "bottom-4"
          }`}
        >
          <div className="text-sm font-bold text-ss-text">📲 Add Sospana Sonke to your home screen</div>
          <p className="mt-1 text-xs text-ss-muted">
            Opens like an app, loads faster, and keeps working when your signal drops.
            {iosHint && !installEv ? " Tap the Share icon, then “Add to Home Screen”." : ""}
          </p>
          <div className="mt-3 flex gap-2">
            {installEv && (
              <button onClick={install} className="rounded-lg bg-navy px-3 py-1.5 text-xs font-semibold text-white">Install</button>
            )}
            <button onClick={dismiss} className="rounded-lg bg-ss-primary-soft px-3 py-1.5 text-xs font-semibold text-ss-text">Not now</button>
          </div>
        </div>
      )}

      <div className="mx-auto mt-2 flex max-w-6xl justify-center px-4 pb-24 md:pb-4">
        <button
          onClick={() => setDataSaver(!saver)}
          aria-pressed={saver}
          className="rounded-full border border-ss-border px-3 py-2.5 text-[11px] text-ss-muted transition hover:text-ss-text md:py-1"
        >
          📶 Data saver: {saver ? "on (no logos)" : "off"}
        </button>
      </div>
    </>
  );
}
