'use client'

/**
 * Theme Toggle Button Component
 *
 * A button that toggles between light and dark themes.
 * Uses sun/moon icons from lucide-react to indicate current theme.
 *
 * Features:
 * - Glassmorphic button styling matching Header design
 * - Smooth icon transition animations
 * - Accessible with aria-label
 * - Persists theme preference via Zustand store
 */

import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '@/lib/stores/themeStore'

export function ThemeToggle() {
  const { theme, toggleTheme } = useThemeStore()

  return (
    <button
      onClick={toggleTheme}
      className="
        relative p-2 rounded-lg glass-card
        hover:bg-white/50 dark:hover:bg-gray-800/50
        transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-accent-blue/50
      "
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <Moon
          className="h-5 w-5 text-gray-700 dark:text-gray-300 transition-transform duration-200 hover:rotate-12"
          aria-hidden="true"
        />
      ) : (
        <Sun
          className="h-5 w-5 text-gray-700 dark:text-gray-300 transition-transform duration-200 hover:rotate-45"
          aria-hidden="true"
        />
      )}
    </button>
  )
}
