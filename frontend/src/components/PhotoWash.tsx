"use client";

import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/** A photographic header wash behind every signed-in (and other internal)
 * page. The landing page and the auth screens paint their own full-bleed
 * photographs, so they opt out. Decorative only — hidden from assistive tech. */

type Scene = { src: string; position?: string };

const SCENES: { test: (path: string) => boolean; scene: Scene }[] = [
  { test: (p) => p.startsWith("/dashboard"), scene: { src: "/photos/workplace.jpg", position: "center 20%" } },
  { test: (p) => p.startsWith("/agent") || p.startsWith("/matches"), scene: { src: "/photos/nairobi.jpg", position: "center" } },
  { test: (p) => p.startsWith("/companies") || p.startsWith("/coverage"), scene: { src: "/photos/cape-town-waterfront.jpg", position: "center" } },
  { test: (p) => p.startsWith("/universities") || p.startsWith("/colleges"), scene: { src: "/photos/marrakech.jpg", position: "center" } },
  { test: (p) => p.startsWith("/hospitals"), scene: { src: "/photos/cape-town-coast.jpg", position: "center" } },
  { test: (p) => p.startsWith("/profile") || p.startsWith("/master-cv") || p.startsWith("/tailor") || p.startsWith("/security"), scene: { src: "/photos/professional.jpg", position: "center 15%" } },
  { test: (p) => p.startsWith("/applications"), scene: { src: "/photos/office.jpg", position: "center" } },
  { test: (p) => p.startsWith("/admin"), scene: { src: "/photos/lagos.jpg", position: "center" } },
  { test: (p) => p.startsWith("/donate"), scene: { src: "/photos/mara-sunset.jpg", position: "center" } },
  { test: (p) => p.startsWith("/messages") || p.startsWith("/notifications"), scene: { src: "/photos/cape-town-coast.jpg", position: "center" } },
];

const FALLBACK: Scene = { src: "/photos/mara-sunset.jpg", position: "center" };

function sceneFor(path: string): Scene | null {
  if (path === "/" || path.startsWith("/login") || path.startsWith("/register") || path.startsWith("/forgot-password") || path.startsWith("/reset-password")) return null;
  return SCENES.find((s) => s.test(path))?.scene ?? FALLBACK;
}

export default function PhotoWash() {
  const path = usePathname() || "/";
  const scene = sceneFor(path);
  const [shift, setShift] = useState(0);

  useEffect(() => {
    setShift(0);
    if (!scene) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;
    const onScroll = () => setShift(Math.min(window.scrollY * 0.15, 56));
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [path, scene]);

  if (!scene) return null;

  return (
    <div className="photo-wash" aria-hidden="true">
      <div
        className="absolute inset-x-0 top-0 h-[130%]"
        style={{ transform: `translate3d(0, ${shift}px, 0) scale(1.08)` }}
      >
        <Image
          src={scene.src}
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ objectPosition: scene.position || "center" }}
        />
      </div>
      <div className="photo-wash-scrim absolute inset-0" />
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-[0.18] mix-blend-overlay" />
    </div>
  );
}
