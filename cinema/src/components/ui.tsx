import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-amber text-stone-950 hover:bg-amber/90",
        quiet: "border border-white/20 bg-white/5 text-ink hover:bg-white/10",
        ghost: "text-ink hover:bg-white/10",
        danger: "bg-coral text-white hover:bg-coral/90",
      },
      size: {
        default: "h-10",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-5 text-base",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex items-center rounded-full border border-white/15 bg-black/40 px-2 py-0.5 text-[11px] font-semibold tracking-wide", className)}>
      {children}
    </span>
  );
}
