import { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
}

/**
 * Card Component with Liquid Glass Design
 *
 * Features:
 * - Glassmorphism effect (backdrop-filter blur)
 * - Optional hover 3D transform
 * - Configurable padding
 * - Elastic bounce-in animation
 *
 * Reference: design-tokens.json Section "components.glassCard"
 */
export function Card({
  children,
  hover = true,
  padding = "md",
  className,
  ...props
}: CardProps) {
  const paddingStyles = {
    none: "",
    sm: "p-3",
    md: "p-6",
    lg: "p-8",
  };

  return (
    <div
      className={cn(
        "glass-card",
        paddingStyles[padding],
        hover && "hover:scale-[1.02]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
