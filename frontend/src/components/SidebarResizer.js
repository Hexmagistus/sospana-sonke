"use client";
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SidebarResizer = SidebarResizer;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const sidebarWidth_1 = require("../lib/explorer/sidebarWidth");
/** Draggable divider between the country list and the map. Desktop only (hidden below lg). */
function SidebarResizer({ width, onChange, containerRef, controls, label = "Resize the country list" }) {
    const dragging = (0, react_1.useRef)(false);
    const last = (0, react_1.useRef)(width);
    last.current = width;
    (0, react_1.useEffect)(() => () => { dragging.current = false; }, []);
    function down(e) {
        if (e.button !== 0)
            return;
        dragging.current = true;
        e.currentTarget.setPointerCapture(e.pointerId);
        e.preventDefault();
    }
    function move(e) {
        if (!dragging.current)
            return;
        const left = containerRef.current?.getBoundingClientRect().left ?? 0;
        onChange((0, sidebarWidth_1.widthFromPointer)(e.clientX, left), false);
    }
    function up(e) {
        if (!dragging.current)
            return;
        dragging.current = false;
        try {
            e.currentTarget.releasePointerCapture(e.pointerId);
        }
        catch { /* already released */ }
        onChange((0, sidebarWidth_1.clampSidebarWidth)(last.current), true);
    }
    function key(e) {
        const next = (0, sidebarWidth_1.widthAfterKey)(width, e.key, e.shiftKey);
        if (next === null)
            return;
        e.preventDefault();
        onChange(next, true);
    }
    return ((0, jsx_runtime_1.jsx)("div", { role: "separator", "aria-orientation": "vertical", "aria-label": label, "aria-controls": controls, "aria-valuenow": width, "aria-valuemin": sidebarWidth_1.SIDEBAR_MIN, "aria-valuemax": sidebarWidth_1.SIDEBAR_MAX, "aria-valuetext": `${width} pixels wide`, tabIndex: 0, title: "Drag to resize. Double-click to reset.", "data-testid": "sidebar-resizer", onPointerDown: down, onPointerMove: move, onPointerUp: up, onPointerCancel: up, onDoubleClick: () => onChange(sidebarWidth_1.SIDEBAR_DEFAULT, true), onKeyDown: key, className: "group relative z-10 hidden w-2 shrink-0 cursor-col-resize touch-none select-none bg-white/10 outline-none transition-colors hover:bg-gold/40 focus-visible:bg-gold/60 lg:block", children: (0, jsx_runtime_1.jsx)("span", { "aria-hidden": true, className: "absolute left-1/2 top-1/2 flex h-9 w-5 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-md border border-white/25 bg-[#0a1a30] text-[11px] font-bold leading-none text-[#ffe08a] shadow group-hover:border-gold group-focus-visible:border-gold", children: "\u21D4" }) }));
}
