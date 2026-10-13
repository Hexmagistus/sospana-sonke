"use client";

import { useEffect, useState, type ComponentType } from "react";
import { GlobeFallback } from "@/components/home/GlobeFallback";
import { canMountShowpiece, readShowpieceSignals } from "@/lib/showpieceGate";

/**
 * The painted globe is always here. WebGL is a second layer in the same box,
 * and only after the page is idle on a device that can spare it.
 */
export function HeroShowpiece() {
  const [Canvas, setCanvas] = useState<ComponentType | null>(null);

  useEffect(() => {
    if (!canMountShowpiece(readShowpieceSignals())) return;
    let cancel = false;
    const start = () => {
      import("./ShowpieceCanvas")
        .then((mod) => {
          if (!cancel) setCanvas(() => mod.ShowpieceCanvas);
        })
        .catch(() => {});
    };
    if (typeof window.requestIdleCallback === "function") {
      const id = window.requestIdleCallback(start, { timeout: 2500 });
      return () => {
        cancel = true;
        window.cancelIdleCallback(id);
      };
    }
    const timer = window.setTimeout(start, 1600);
    return () => {
      cancel = true;
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <div className="ss-showpiece">
      <GlobeFallback />
      {Canvas ? <Canvas /> : null}
    </div>
  );
}
