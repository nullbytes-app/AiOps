import { TextareaHTMLAttributes, forwardRef, useId } from "react";
import { cn } from "@/lib/utils/cn";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helpText?: string;
}

/**
 * Textarea Component with Liquid Glass Design
 *
 * Features:
 * - Glass-style textarea with backdrop blur
 * - Optional label and help text
 * - Error state with red accent
 * - Focus ring with accent-blue
 * - Auto-resizes with content
 * - Proper label association for accessibility
 *
 * Compatible with React Hook Form via forwardRef
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helpText, className, id, ...props }, ref) => {
    const generatedId = useId();
    const textareaId = id || generatedId;
    const errorId = `${textareaId}-error`;
    const helpTextId = `${textareaId}-help`;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={textareaId} className="block text-sm font-medium text-text-primary mb-2">
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          aria-describedby={error ? errorId : helpText ? helpTextId : undefined}
          className={cn(
            "w-full px-4 py-2 rounded-lg bg-white/50 border border-white/50 text-text-primary placeholder-text-secondary",
            "focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent",
            "transition-all duration-fast",
            "backdrop-blur-glass",
            "resize-y min-h-[100px]",
            error && "border-red-500 focus:ring-red-500",
            className
          )}
          {...props}
        />
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

Textarea.displayName = "Textarea";
