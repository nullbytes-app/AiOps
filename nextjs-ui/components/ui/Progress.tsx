import * as React from "react";
import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils/cn";

interface ProgressProps
  extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  indicatorClassName?: string;
}

/**
 * Progress Component with Liquid Glass Design
 *
 * A visual indicator showing completion progress.
 * Used for budget utilization, task completion, loading states.
 *
 * @param value - Progress value (0-100)
 * @param indicatorClassName - Custom classes for the indicator bar
 * @param className - Custom classes for the root container
 *
 * @example
 * ```tsx
 * <Progress value={75} indicatorClassName="bg-green-500" />
 * <Progress value={95} indicatorClassName="bg-red-500" />
 * ```
 *
 * Reference: shadcn/ui Progress component adapted for Liquid Glass design
 */
const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(({ className, value, indicatorClassName, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      "relative h-2 w-full overflow-hidden rounded-full bg-gray-200",
      className
    )}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className={cn(
        "h-full w-full flex-1 bg-accent-blue transition-all duration-medium",
        indicatorClassName
      )}
      style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
    />
  </ProgressPrimitive.Root>
));
Progress.displayName = ProgressPrimitive.Root.displayName;

export { Progress };
