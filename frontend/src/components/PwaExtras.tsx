"use client";

import { useEffect, useState } from "react";
import { DATA_SAVER_EVENT, isDataSaver, setDataSaver } from "@/lib/dataSaver";

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };
const DISMISS_KEY = "ss-install-dismissed";

/** Install-to-home-screen prompt, offline banner and the data-saver switch. */
export default function PwaExtras() {
  const [installEv, setInstallEv] = useState<InstallEvent | null>(null);
  const [iosHint, setIosHint] = useState(false);
  const [offline, setOffline] = useState(false);
  const [saver, setSaver] = useState(false);

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

    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
      window.removeEventListener(DATA_SAVER_EVENT, sync);
      window.removeEventListener("beforeinstallprompt", bip);
    };
  }, []);

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

      {(installEv || iosHint) && (
        <div className="fixed inset-x-3 bottom-20 z-[55] mx-auto max-w-sm rounded-2xl border border-gray-200 bg-white p-4 shadow-xl md:bottom-4 md:left-auto md:right-4 md:mx-0">
          <div className="text-sm font-bold text-navy">📲 Add Sospana Sonke to your home screen</div>
          <p className="mt-1 text-xs text-gray-600">
            Opens like an app, loads faster, and keeps working when your signal drops.
            {iosHint && !installEv ? " Tap the Share icon, then “Add to Home Screen”." : ""}
          </p>
          <div className="mt-3 flex gap-2">
            {installEv && (
              <button onClick={install} className="rounded-lg bg-navy px-3 py-1.5 text-xs font-semibold text-white">Install</button>
            )}
            <button onClick={dismiss} className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-700">Not now</button>
          </div>
        </div>
      )}

      <div className="mx-auto mt-2 flex max-w-6xl justify-center px-4 pb-24 md:pb-4">
        <button
          onClick={() => setDataSaver(!saver)}
          aria-pressed={saver}
          className="rounded-full border border-ss-border px-3 py-1 text-[11px] text-ss-muted transition hover:text-ss-text"
        >
          📶 Data saver: {saver ? "on (no logos)" : "off"}
        </button>
      </div>
    </>
  );
}
