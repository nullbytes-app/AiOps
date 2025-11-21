import { ReactNode } from "react";

interface KbdProps {
  children: ReactNode;
  className?: string;
}

/**
 * Kbd Component
 *
 * Displays keyboard keys in a styled badge format.
 * Used by ShortcutsModal and CommandPalette to show keyboard shortcuts.
 *
 * @example
 * ```tsx
 * <Kbd>⌘</Kbd> + <Kbd>K</Kbd>
 * ```
 *
 * Reference: Story 6 AC-2 (Keyboard Shortcuts System)
 */
export function Kbd({ children, className = "" }: KbdProps) {
  return (
    <kbd
      className={`inline-flex items-center justify-center px-2 py-1 min-w-[2rem] text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded shadow-sm ${className}`}
    >
      {children}
    </kbd>
  );
}
