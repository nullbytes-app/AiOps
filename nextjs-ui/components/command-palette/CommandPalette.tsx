"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Home,
  Cpu,
  PlayCircle,
  ListOrdered,
  Settings,
  Building2,
  Plug,
  FileCode,
  Wrench,
  Search,
  Moon,
  Sun,
  HelpCircle,
  Plus,
  RefreshCw,
  Download,
  type LucideIcon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { formatKeys } from "@/lib/config/shortcuts";

/**
 * Command Palette Item Types
 */
interface CommandItem {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  keywords: string[];
  onSelect: () => void;
  shortcut?: string;
}

interface CommandGroup {
  heading: string;
  items: CommandItem[];
}

/**
 * CommandPalette Component
 *
 * Global command palette (⌘K / Ctrl+K) for quick navigation and actions.
 * Features:
 * - Fuzzy search across all pages, actions, and settings
 * - Keyboard navigation (arrow keys, enter, escape)
 * - Recent searches (localStorage)
 * - Virtualized results (cmdk handles automatically)
 * - Categorized results (Pages | Actions | Settings | Help)
 *
 * Reference: Story 6 AC-1 (Command Palette)
 * Context7 best practices: /pacocoursey/cmdk
 */
export function CommandPalette() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  /**
   * Load recent searches from localStorage
   */
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("command-palette-recent");
      if (stored) {
        try {
          setRecentSearches(JSON.parse(stored));
        } catch {
          setRecentSearches([]);
        }
      }
    }
  }, []);

  /**
   * Save search to recent searches
   */
  const saveRecentSearch = useCallback((searchTerm: string) => {
    if (!searchTerm.trim()) return;

    setRecentSearches((prev) => {
      const updated = [searchTerm, ...prev.filter((s) => s !== searchTerm)].slice(0, 5);
      localStorage.setItem("command-palette-recent", JSON.stringify(updated));
      return updated;
    });
  }, []);

  /**
   * Handle ⌘K / Ctrl+K keyboard shortcut
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  /**
   * Handle item selection
   */
  const handleSelect = useCallback(
    (item: CommandItem) => {
      item.onSelect();
      saveRecentSearch(item.name);
      setOpen(false);
      setSearch("");
    },
    [saveRecentSearch]
  );

  /**
   * Command Groups
   */
  const commandGroups = useMemo((): CommandGroup[] => {
    return [
      {
        heading: "Pages",
        items: [
          {
            id: "dashboard",
            name: "Dashboard",
            description: "Overview and metrics",
            icon: Home,
            keywords: ["home", "overview", "metrics", "stats"],
            onSelect: () => router.push("/dashboard"),
            shortcut: "g>d",
          },
          {
            id: "agents",
            name: "Agents",
            description: "Manage AI agents",
            icon: Cpu,
            keywords: ["ai", "bots", "agents", "manage"],
            onSelect: () => router.push("/dashboard/agents"),
            shortcut: "g>a",
          },
          {
            id: "executions",
            name: "Executions",
            description: "View execution history",
            icon: PlayCircle,
            keywords: ["history", "runs", "logs", "executions"],
            onSelect: () => router.push("/dashboard/executions"),
            shortcut: "g>e",
          },
          {
            id: "queue",
            name: "Queue Management",
            description: "Monitor job queue",
            icon: ListOrdered,
            keywords: ["jobs", "tasks", "queue", "celery"],
            onSelect: () => router.push("/dashboard/queue"),
            shortcut: "g>q",
          },
          {
            id: "tenants",
            name: "Tenants",
            description: "Manage tenants",
            icon: Building2,
            keywords: ["clients", "organizations", "tenants"],
            onSelect: () => router.push("/dashboard/tenants"),
            shortcut: "g>t",
          },
          {
            id: "providers",
            name: "LLM Providers",
            description: "Configure LLM providers",
            icon: Plug,
            keywords: ["openai", "anthropic", "providers", "llm"],
            onSelect: () => router.push("/dashboard/providers"),
            shortcut: "g>p",
          },
          {
            id: "plugins",
            name: "Plugins",
            description: "Manage plugins",
            icon: Plug,
            keywords: ["extensions", "integrations", "plugins"],
            onSelect: () => router.push("/dashboard/plugins"),
          },
          {
            id: "prompts",
            name: "System Prompts",
            description: "Edit system prompts",
            icon: FileCode,
            keywords: ["templates", "prompts", "instructions"],
            onSelect: () => router.push("/dashboard/prompts"),
          },
          {
            id: "tools",
            name: "Tools",
            description: "Manage agent tools",
            icon: Wrench,
            keywords: ["functions", "tools", "actions"],
            onSelect: () => router.push("/dashboard/tools"),
          },
          {
            id: "settings",
            name: "Settings",
            description: "Application settings",
            icon: Settings,
            keywords: ["config", "preferences", "settings"],
            onSelect: () => router.push("/dashboard/settings"),
            shortcut: "g>s",
          },
        ],
      },
      {
        heading: "Actions",
        items: [
          {
            id: "create-agent",
            name: "Create Agent",
            description: "Create a new AI agent",
            icon: Plus,
            keywords: ["new", "add", "create", "agent"],
            onSelect: () => router.push("/dashboard/agents?action=create"),
            shortcut: "c (on Agents page)",
          },
          {
            id: "refresh-data",
            name: "Refresh Data",
            description: "Reload current page data",
            icon: RefreshCw,
            keywords: ["reload", "refresh", "update"],
            onSelect: () => window.location.reload(),
            shortcut: "r (on some pages)",
          },
          {
            id: "export-csv",
            name: "Export to CSV",
            description: "Download data as CSV",
            icon: Download,
            keywords: ["export", "download", "csv"],
            onSelect: () => {
              // Will be implemented per-page
              console.log("Export CSV action");
            },
            shortcut: "x (on some pages)",
          },
        ],
      },
      {
        heading: "Settings",
        items: [
          {
            id: "toggle-theme",
            name: "Toggle Theme",
            description: `Switch to ${theme === "dark" ? "light" : "dark"} mode`,
            icon: theme === "dark" ? Sun : Moon,
            keywords: ["dark", "light", "theme", "appearance"],
            onSelect: () => setTheme(theme === "dark" ? "light" : "dark"),
            shortcut: "⌘⇧D",
          },
          {
            id: "search-focus",
            name: "Focus Search",
            description: "Focus global search input",
            icon: Search,
            keywords: ["find", "search", "query"],
            onSelect: () => {
              // Will be implemented with global search
              console.log("Focus search action");
            },
            shortcut: "/",
          },
        ],
      },
      {
        heading: "Help",
        items: [
          {
            id: "keyboard-shortcuts",
            name: "Keyboard Shortcuts",
            description: "View all keyboard shortcuts",
            icon: HelpCircle,
            keywords: ["help", "shortcuts", "keys", "hotkeys"],
            onSelect: () => {
              // Will open ShortcutsModal
              const event = new CustomEvent("open-shortcuts-modal");
              window.dispatchEvent(event);
            },
            shortcut: "?",
          },
        ],
      },
    ];
  }, [router, theme, setTheme]);

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Global Command Menu"
      className="fixed inset-0 z-[9999] bg-black/50 backdrop-blur-sm"
    >
      <div className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-2xl glass-card border-2 border-gray-200 dark:border-gray-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Search Input */}
        <Command.Input
          value={search}
          onValueChange={setSearch}
          placeholder="Search pages, actions, or shortcuts..."
          className="w-full px-6 py-4 text-lg bg-transparent border-none outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
          autoFocus
        />

        {/* Results List */}
        <Command.List className="max-h-[400px] overflow-y-auto border-t border-gray-200 dark:border-gray-700 p-2">
          <Command.Empty className="py-12 text-center text-gray-500 dark:text-gray-400">
            No results found for &quot;{search}&quot;
          </Command.Empty>

          {/* Recent Searches (only show when no search query) */}
          {!search && recentSearches.length > 0 && (
            <Command.Group heading="Recent Searches" className="px-2 py-2">
              {recentSearches.map((term, idx) => (
                <Command.Item
                  key={`recent-${idx}`}
                  value={term}
                  onSelect={() => setSearch(term)}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 data-[selected=true]:bg-gray-100 dark:data-[selected=true]:bg-gray-800"
                >
                  <Search size={18} className="text-gray-400" />
                  <span className="flex-1 text-sm">{term}</span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {/* Command Groups */}
          {commandGroups.map((group) => (
            <Command.Group
              key={group.heading}
              heading={group.heading}
              className="px-2 py-2"
            >
              <div className="px-2 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {group.heading}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <Command.Item
                    key={item.id}
                    value={`${item.name} ${item.description} ${item.keywords.join(" ")}`}
                    onSelect={() => handleSelect(item)}
                    keywords={item.keywords}
                    className="flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 data-[selected=true]:bg-gray-100 dark:data-[selected=true]:bg-gray-800 transition-colors"
                  >
                    <Icon
                      size={18}
                      className="flex-shrink-0 text-gray-600 dark:text-gray-400"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {item.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {item.description}
                      </div>
                    </div>
                    {item.shortcut && (
                      <div className="ml-auto text-xs text-gray-400 dark:text-gray-500">
                        {formatKeys(item.shortcut)}
                      </div>
                    )}
                  </Command.Item>
                );
              })}
            </Command.Group>
          ))}
        </Command.List>

        {/* Footer Hint */}
        <div className="flex items-center justify-between px-4 py-2 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center gap-4">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700">↑↓</kbd>{" "}
              to navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700">↵</kbd>{" "}
              to select
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700">esc</kbd>{" "}
              to close
            </span>
          </div>
        </div>
      </div>
    </Command.Dialog>
  );
}
