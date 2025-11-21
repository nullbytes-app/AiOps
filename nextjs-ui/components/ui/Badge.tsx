import { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
  size?: "sm" | "md";
}

/**
 * Badge Component for status indicators
 *
 * Variants:
 * - default: Neutral gray
 * - success: Green accent
 * - warning: Orange accent
 * - error: Red accent
 * - info: Blue accent
 *
 * Reference: design-tokens.json colors.accent
 */
export function Badge({
  children,
  variant = "default",
  size = "md",
  className,
  ...props
}: BadgeProps) {
  const baseStyles =
    "inline-flex items-center gap-1 rounded-full font-medium whitespace-nowrap";

  const variantStyles = {
    default: "bg-gray-100 text-gray-700",
    success: "bg-accent-green/20 text-accent-green",
    warning: "bg-accent-orange/20 text-accent-orange",
    error: "bg-red-100 text-red-700",
    info: "bg-accent-blue/20 text-accent-blue",
  };

  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
  };

  return (
    <span
      className={cn(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
