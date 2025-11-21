import { InputHTMLAttributes, forwardRef, ReactNode, useId } from "react";
import { cn } from "@/lib/utils/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helpText?: string;
  icon?: ReactNode;
}

/**
 * Input Component with Liquid Glass Design
 *
 * Features:
 * - Glass-style input with backdrop blur
 * - Optional label and help text
 * - Error state with red accent
 * - Focus ring with accent-blue
 * - Proper label association for accessibility
 *
 * Reference: design-tokens.json
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helpText, icon, className, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helpTextId = `${inputId}-help`;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-text-primary mb-2">
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-describedby={error ? errorId : helpText ? helpTextId : undefined}
            className={cn(
              "w-full px-4 py-2 rounded-lg bg-white/50 border border-white/50 text-text-primary placeholder-text-secondary",
              "focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent",
              "transition-all duration-fast",
              "backdrop-blur-glass",
              error && "border-red-500 focus:ring-red-500",
              icon && "pl-10",
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <p id={errorId} className="mt-1 text-sm text-red-500">{error}</p>
        )}
        {helpText && !error && (
          <p id={helpTextId} className="mt-1 text-sm text-text-secondary">{helpText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
