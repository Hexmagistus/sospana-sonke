"use client";
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.categoryOptionText = categoryOptionText;
exports.CategorySelect = CategorySelect;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
/** Display text of one option: "Municipalities 262". */
function categoryOptionText(o) {
    return o.count === null ? o.label : `${o.label} ${o.count.toLocaleString()}`;
}
/** One category dropdown (native select: keyboard and mobile friendly). Counts are for the selected country. */
function CategorySelect({ options, value, onChange, scope }) {
    const id = (0, react_1.useId)();
    return ((0, jsx_runtime_1.jsxs)("div", { className: "mx-auto flex w-full max-w-md flex-col items-stretch gap-1 pb-3 sm:flex-row sm:items-center sm:justify-center sm:gap-2", children: [(0, jsx_runtime_1.jsx)("label", { htmlFor: id, className: "text-center text-[11px] font-bold uppercase tracking-wider text-blue-200 sm:text-left", children: "Category" }), (0, jsx_runtime_1.jsx)("select", { id: id, value: value, onChange: (e) => onChange(e.target.value), "aria-describedby": `${id}-hint`, className: "min-w-0 flex-1 rounded-lg border border-white/20 bg-[#071528] px-3 py-2 text-sm font-semibold text-white focus:border-gold", children: options.map((o) => ((0, jsx_runtime_1.jsx)("option", { value: o.id, children: categoryOptionText(o) }, o.id))) }), (0, jsx_runtime_1.jsxs)("span", { id: `${id}-hint`, className: "sr-only", children: ["Counts are for ", scope, "."] })] }));
}
