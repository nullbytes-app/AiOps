"use client";

import { ReactNode, useEffect } from "react";
import { useThemeStore } from "@/lib/stores/themeStore";

interface ThemeProviderProps {
  children: ReactNode;
}

/**
 * Theme provider for managing application theme
 *
 * Features:
 * - Manages light/dark mode using Zustand store
 * - Applies theme class to document root
 * - Persists theme preference to localStorage
 * - Supports theme toggle via ThemeToggle component
 *
 * Reference: tech-spec Section 2.3.2
 */
export function ThemeProvider({ children }: ThemeProviderProps) {
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    // Apply theme class to document root
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  return <>{children}</>;
}
