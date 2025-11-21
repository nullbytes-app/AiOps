import { SelectHTMLAttributes, forwardRef, useId } from "react";
import { cn } from "@/lib/utils/cn";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helpText?: string;
  options: SelectOption[];
  placeholder?: string;
}

/**
 * Select Component with Liquid Glass Design
 *
 * Features:
 * - Glass-style select with backdrop blur
 * - Optional label and help text
 * - Error state with red accent
 * - Focus ring with accent-blue
 * - Proper label association for accessibility
 *
 * Compatible with React Hook Form via forwardRef
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, helpText, options, placeholder, className, id, ...props }, ref) => {
    const generatedId = useId();
    const selectId = id || generatedId;
    const errorId = `${selectId}-error`;
    const helpTextId = `${selectId}-help`;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={selectId} className="block text-sm font-medium text-text-primary mb-2">
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          aria-describedby={error ? errorId : helpText ? helpTextId : undefined}
          className={cn(
            "w-full px-4 py-2 rounded-lg bg-white/50 border border-white/50 text-text-primary",
            "focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent",
            "transition-all duration-fast",
            "backdrop-blur-glass",
            error && "border-red-500 focus:ring-red-500",
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
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

Select.displayName = "Select";
