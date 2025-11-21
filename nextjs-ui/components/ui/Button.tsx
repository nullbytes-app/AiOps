import { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

/**
 * Button Component with Liquid Glass Design
 *
 * Variants:
 * - primary: Accent blue with white text
 * - secondary: Glass background with accent hover
 * - ghost: Transparent with hover effect
 * - danger: Red accent for destructive actions
 *
 * Reference: design-tokens.json Section "components.button"
 */
export function Button({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  className,
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-all duration-fast focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";

  const variantStyles = {
    primary:
      "bg-accent-blue text-white hover:bg-accent-blue/90 shadow-sm hover:shadow-md",
    secondary:
      "glass-card text-text-primary hover:bg-white/80 hover:shadow-lg",
    ghost:
      "text-text-primary hover:bg-white/50",
    danger:
      "bg-red-500 text-white hover:bg-red-600 shadow-sm hover:shadow-md",
  };

  const sizeStyles = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-body",
    lg: "px-6 py-3 text-lg",
  };

  return (
    <button
      className={cn(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          <span>Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
