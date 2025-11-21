"use client";

import { ReactNode } from "react";
import { useKeyboardShortcuts } from "@/lib/hooks/useKeyboardShortcuts";
import { CommandPalette } from "@/components/command-palette/CommandPalette";
import { ShortcutsModal } from "@/components/shortcuts/ShortcutsModal";

interface KeyboardShortcutsProviderProps {
  children: ReactNode;
}

/**
 * Keyboard Shortcuts Provider
 *
 * Registers all keyboard shortcuts and provides command palette + shortcuts modal.
 * Components:
 * - useKeyboardShortcuts hook (registers all shortcuts)
 * - CommandPalette (⌘K / Ctrl+K)
 * - ShortcutsModal (? key)
 *
 * Reference: Story 6 AC-1 & AC-2
 */
export function KeyboardShortcutsProvider({ children }: KeyboardShortcutsProviderProps) {
  // Register all keyboard shortcuts
  useKeyboardShortcuts();

  return (
    <>
      {children}
      <CommandPalette />
      <ShortcutsModal />
    </>
  );
}
