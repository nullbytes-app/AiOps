"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useHotkeys } from "react-hotkeys-hook";
import { useTheme } from "next-themes";
import {
  GLOBAL_SHORTCUTS,
  NAVIGATION_SHORTCUTS,
  PAGE_ACTION_SHORTCUTS,
} from "@/lib/config/shortcuts";

/**
 * useKeyboardShortcuts Hook
 *
 * Registers all keyboard shortcuts defined in the shortcuts config.
 * Features:
 * - Global shortcuts (⌘K, ⌘B, /, ⌘⇧D, ?, Esc)
 * - Navigation shortcuts (g>d, g>a, etc. vim-style)
 * - Page-specific shortcuts (c for create on agents page, etc.)
 * - Cross-platform modifier key normalization (mod = ⌘ on Mac, Ctrl on Windows)
 *
 * Reference: Story 6 AC-2 (Keyboard Shortcuts System)
 * Context7 best practices: /johannesklauss/react-hotkeys-hook
 */
export function useKeyboardShortcuts() {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  /**
   * Determine current page scope for page-specific shortcuts
   */
  const getCurrentScope = (): string | undefined => {
    if (pathname?.includes("/agents")) return "agents";
    if (pathname?.includes("/executions")) return "executions";
    if (pathname?.includes("/queue")) return "queue";
    return undefined;
  };

  /**
   * Global Shortcuts
   */

  // ⌘K / Ctrl+K - Open command palette (handled by CommandPalette itself)
  // No need to register here, CommandPalette component handles it

  // ⌘B / Ctrl+B - Toggle sidebar
  useHotkeys(
    "mod+b",
    (e) => {
      e.preventDefault();
      // Dispatch custom event for sidebar toggle
      const event = new CustomEvent("toggle-sidebar");
      window.dispatchEvent(event);
    },
    [],
    {
      enableOnFormTags: false, // Don't trigger in form inputs
    }
  );

  // / - Focus global search
  useHotkeys(
    "/",
    (e) => {
      // Only trigger if not in an input
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      e.preventDefault();
      // Dispatch custom event for search focus
      const event = new CustomEvent("focus-global-search");
      window.dispatchEvent(event);
    },
    [],
    {
      enableOnFormTags: false,
    }
  );

  // ⌘⇧D / Ctrl+Shift+D - Toggle theme
  useHotkeys(
    "mod+shift+d",
    (e) => {
      e.preventDefault();
      setTheme(theme === "dark" ? "light" : "dark");
    },
    [theme, setTheme],
    {
      enableOnFormTags: false,
    }
  );

  // ? - Open shortcuts help modal
  useHotkeys(
    "shift+/", // '?' is Shift+/
    (e) => {
      // Only trigger if not in an input
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      e.preventDefault();
      // Dispatch custom event for shortcuts modal
      const event = new CustomEvent("open-shortcuts-modal");
      window.dispatchEvent(event);
    },
    [],
    {
      enableOnFormTags: false,
    }
  );

  // Esc - Close any modal/dropdown (handled by individual components)

  /**
   * Navigation Shortcuts (vim-style sequences)
   */

  // g>d - Go to Dashboard
  useHotkeys(
    "g>d",
    (e) => {
      e.preventDefault();
      router.push("/dashboard");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  // g>a - Go to Agents
  useHotkeys(
    "g>a",
    (e) => {
      e.preventDefault();
      router.push("/dashboard/agents");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  // g>e - Go to Executions
  useHotkeys(
    "g>e",
    (e) => {
      e.preventDefault();
      router.push("/dashboard/executions");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  // g>q - Go to Queue
  useHotkeys(
    "g>q",
    (e) => {
      e.preventDefault();
      router.push("/dashboard/queue");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  // g>s - Go to Settings
  useHotkeys(
    "g>s",
    (e) => {
      e.preventDefault();
      router.push("/dashboard/settings");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  // g>t - Go to Tenants
  useHotkeys(
    "g>t",
    (e) => {
      e.preventDefault();
      router.push("/dashboard/tenants");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  // g>p - Go to Providers
  useHotkeys(
    "g>p",
    (e) => {
      e.preventDefault();
      router.push("/dashboard/providers");
    },
    [router],
    {
      enableOnFormTags: false,
      sequenceTimeoutMs: 1000,
    }
  );

  /**
   * Page-Specific Shortcuts
   */
  const currentScope = getCurrentScope();

  // c - Create (on agents page)
  useHotkeys(
    "c",
    (e) => {
      if (currentScope !== "agents") return;
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      e.preventDefault();
      // Dispatch custom event for create action
      const event = new CustomEvent("create-agent");
      window.dispatchEvent(event);
    },
    [currentScope],
    {
      enableOnFormTags: false,
    }
  );

  // r - Refresh data (on executions page)
  useHotkeys(
    "r",
    (e) => {
      if (currentScope !== "executions") return;
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      e.preventDefault();
      // Dispatch custom event for refresh
      const event = new CustomEvent("refresh-data");
      window.dispatchEvent(event);
    },
    [currentScope],
    {
      enableOnFormTags: false,
    }
  );

  // x - Export CSV (on executions page)
  useHotkeys(
    "x",
    (e) => {
      if (currentScope !== "executions") return;
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      e.preventDefault();
      // Dispatch custom event for export
      const event = new CustomEvent("export-csv");
      window.dispatchEvent(event);
    },
    [currentScope],
    {
      enableOnFormTags: false,
    }
  );

  // p - Pause/Resume queue (on queue page)
  useHotkeys(
    "p",
    (e) => {
      if (currentScope !== "queue") return;
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      e.preventDefault();
      // Dispatch custom event for pause/resume
      const event = new CustomEvent("toggle-queue");
      window.dispatchEvent(event);
    },
    [currentScope],
    {
      enableOnFormTags: false,
    }
  );

  // Log registered shortcuts (dev only)
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.log("[useKeyboardShortcuts] Registered shortcuts:", {
        global: GLOBAL_SHORTCUTS.map((s) => s.keys),
        navigation: NAVIGATION_SHORTCUTS.map((s) => s.keys),
        pageActions: PAGE_ACTION_SHORTCUTS.filter((s) => s.scope === currentScope).map(
          (s) => s.keys
        ),
      });
    }
  }, [currentScope]);
}
