import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

interface LoadingProps extends HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg";
  text?: string;
}

/**
 * Loading Spinner Component
 *
 * Features:
 * - Animated spinning circle
 * - Multiple sizes
 * - Optional loading text
 * - Uses accent-blue color
 *
 * Reference: design-tokens.json colors.accent.blue
 */
export function Loading({
  size = "md",
  text,
  className,
  ...props
}: LoadingProps) {
  const sizeStyles = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3", className)}
      {...props}
    >
      <div
        className={cn(
          sizeStyles[size],
          "border-4 border-accent-blue/20 border-t-accent-blue rounded-full animate-spin"
        )}
      />
      {text && (
        <p className="text-sm text-text-secondary animate-pulse">{text}</p>
      )}
    </div>
  );
}
