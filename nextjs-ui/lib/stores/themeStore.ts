/**
 * Theme Store using Zustand
 *
 * Manages light/dark theme state with localStorage persistence.
 * The theme preference is saved to localStorage and restored on app load.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export type Theme = 'light' | 'dark'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

/**
 * Global theme store
 *
 * Features:
 * - Persists theme preference to localStorage
 * - Provides theme getter and setter
 * - Provides toggleTheme convenience method
 */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'light',
      setTheme: (theme) => set({ theme }),
      toggleTheme: () =>
        set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
    }),
    {
      name: 'theme-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
