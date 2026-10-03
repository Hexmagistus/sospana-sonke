"use client";

import { useEffect, useRef, type KeyboardEvent, type PointerEvent } from "react";
import {
  SIDEBAR_DEFAULT, SIDEBAR_MAX, SIDEBAR_MIN, clampSidebarWidth, widthAfterKey, widthFromPointer,
} from "./sidebarWidth";

type Props = {
  width: number;
  onChange: (px: number, persist: boolean) => void;
  /** The element the separator sits next to (its left edge is the drag origin). */
  containerRef: React.RefObject<HTMLElement | null>;
  controls: string;
  label?: string;
};

/** Draggable divider between the country list and the map. Desktop only (hidden below lg). */
export function SidebarResizer({ width, onChange, containerRef, controls, label = "Resize the country list" }: Props) {
  const dragging = useRef(false);
  const last = useRef(width);
  last.current = width;

  useEffect(() => () => { dragging.current = false; }, []);

  function down(e: PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    dragging.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    e.preventDefault();
  }
  function move(e: PointerEvent<HTMLDivElement>) {
    if (!dragging.current) return;
    const left = containerRef.current?.getBoundingClientRect().left ?? 0;
    onChange(widthFromPointer(e.clientX, left), false);
  }
  function up(e: PointerEvent<HTMLDivElement>) {
    if (!dragging.current) return;
    dragging.current = false;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* already released */ }
    onChange(clampSidebarWidth(last.current), true);
  }
  function key(e: KeyboardEvent<HTMLDivElement>) {
    const next = widthAfterKey(width, e.key, e.shiftKey);
    if (next === null) return;
    e.preventDefault();
    onChange(next, true);
  }

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-controls={controls}
      aria-valuenow={width}
      aria-valuemin={SIDEBAR_MIN}
      aria-valuemax={SIDEBAR_MAX}
      aria-valuetext={`${width} pixels wide`}
      tabIndex={0}
      title="Drag to resize. Double-click to reset."
      data-testid="sidebar-resizer"
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      onDoubleClick={() => onChange(SIDEBAR_DEFAULT, true)}
      onKeyDown={key}
      className="group relative z-10 hidden w-2 shrink-0 cursor-col-resize touch-none select-none bg-white/10 outline-none transition-colors hover:bg-gold/40 focus-visible:bg-gold/60 lg:block"
    >
      <span
        aria-hidden
        className="absolute left-1/2 top-1/2 flex h-9 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-md border border-white/25 bg-[#0a1a30] text-[11px] font-bold leading-none text-[#ffe08a] shadow group-hover:border-gold group-focus-visible:border-gold"
      >
        ⇔
      </span>
    </div>
  );
}
