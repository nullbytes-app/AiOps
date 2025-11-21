import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react';
import { ReactNode, useState, useRef, useEffect } from 'react';

export type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';

export interface TooltipProps {
  /**
   * Content to display in the tooltip
   */
  content: ReactNode;
  /**
   * Element that triggers the tooltip
   */
  children: ReactNode;
  /**
   * Placement of the tooltip relative to the trigger
   */
  placement?: TooltipPlacement;
  /**
   * Delay before showing tooltip (ms)
   */
  delay?: number;
  /**
   * Disable the tooltip
   */
  disabled?: boolean;
  /**
   * Additional CSS classes for the tooltip panel
   */
  className?: string;
}

const placementClasses = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
};

const arrowClasses = {
  top: 'top-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-gray-900 dark:border-t-gray-700',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-gray-900 dark:border-b-gray-700',
  left: 'left-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-gray-900 dark:border-l-gray-700',
  right: 'right-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-gray-900 dark:border-r-gray-700',
};

/**
 * Tooltip component using Headless UI Popover with hover interaction
 *
 * Features:
 * - Hover-based interaction (shows on hover, hides on leave)
 * - 4 placement options (top, bottom, left, right)
 * - Configurable delay
 * - Accessible (ARIA attributes, keyboard support)
 * - Glassmorphism styling
 * - Arrow indicator
 * - Disabled state
 *
 * @example
 * ```tsx
 * <Tooltip content="This is a tooltip" placement="top">
 *   <button>Hover me</button>
 * </Tooltip>
 * ```
 */
export function Tooltip({
  content,
  children,
  placement = 'top',
  delay = 200,
  disabled = false,
  className = '',
}: TooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isHovering && !disabled) {
      timeoutRef.current = setTimeout(() => {
        setIsOpen(true);
      }, delay);
    } else {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      setIsOpen(false);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isHovering, disabled, delay]);

  const handleMouseEnter = () => {
    setIsHovering(true);
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
  };

  const handleFocus = () => {
    if (!disabled) {
      setIsOpen(true);
    }
  };

  const handleBlur = () => {
    setIsOpen(false);
  };

  if (disabled) {
    return <>{children}</>;
  }

  return (
    <Popover className="relative inline-block">
      <PopoverButton
        as="span"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleFocus}
        onBlur={handleBlur}
        className="cursor-default focus:outline-none"
        tabIndex={0}
        aria-describedby={isOpen ? 'tooltip-content' : undefined}
      >
        {children}
      </PopoverButton>

      {isOpen && (
        <PopoverPanel
          static
          id="tooltip-content"
          role="tooltip"
          className={`absolute z-50 ${placementClasses[placement]} pointer-events-none`}
        >
          <div
            className={`
              glass-card
              px-3 py-2
              text-sm
              text-white
              bg-gray-900/90 dark:bg-gray-700/90
              backdrop-blur-sm
              rounded-lg
              shadow-lg
              max-w-xs
              whitespace-nowrap
              ${className}
            `}
          >
            {content}
            {/* Arrow */}
            <div
              className={`absolute w-0 h-0 border-4 ${arrowClasses[placement]}`}
              aria-hidden="true"
            />
          </div>
        </PopoverPanel>
      )}
    </Popover>
  );
}
