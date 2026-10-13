"use client";

import { useEffect } from "react";

const CONTROL = new Set(["INPUT", "TEXTAREA", "SELECT", "BUTTON"]);

function allowed(): boolean {
  return (
    window.matchMedia("(hover: hover) and (pointer: fine)").matches &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** One pointer listener for every shared card. Touch scrolls do not tilt. */
export function CardTilt() {
  useEffect(() => {
    if (!allowed()) return;
    let current: HTMLElement | null = null;
    let frame = 0;
    let lastX = 0;
    let lastY = 0;

    function clear() {
      if (!current) return;
      current.style.transform = "";
      current = null;
    }

    function paint() {
      frame = 0;
      if (!current) return;
      const rect = current.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) return;
      const px = (lastX - rect.left) / rect.width - 0.5;
      const py = (lastY - rect.top) / rect.height - 0.5;
      current.style.transform = `perspective(900px) rotateX(${(-py * 3.5).toFixed(2)}deg) rotateY(${(px * 4.5).toFixed(2)}deg)`;
    }

    function onMove(event: PointerEvent) {
      if (event.pointerType === "touch" || !allowed()) {
        clear();
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (CONTROL.has(target.tagName) || target.closest("[data-tilt-root], .ss-sticky-search, .ss-no-tilt")) {
        clear();
        return;
      }
      const card = target.closest(".ss-card");
      if (!(card instanceof HTMLElement)) {
        clear();
        return;
      }
      if (current && current !== card) current.style.transform = "";
      current = card;
      lastX = event.clientX;
      lastY = event.clientY;
      if (!frame) frame = window.requestAnimationFrame(paint);
    }

    document.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", clear);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      clear();
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", clear);
    };
  }, []);

  return null;
}
