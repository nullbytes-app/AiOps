"use client";

import { useState, useEffect } from "react";
import { X, Search } from "lucide-react";
import { Kbd } from "@/components/ui/Kbd";
import {
  ALL_SHORTCUTS,
  ShortcutConfig,
  formatKeys,
} from "@/lib/config/shortcuts";

/**
 * ShortcutsModal Component
 *
 * Help modal showing all available keyboard shortcuts.
 * Features:
 * - Triggered by '?' key
 * - Organized by category (Global, Navigation, Page Actions, Editing)
 * - Searchable shortcuts filter
 * - Escape key to close
 * - Click outside to close
 *
 * Reference: Story 6 AC-2 (Keyboard Shortcuts System)
 */
export function ShortcutsModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  /**
   * Listen for custom event to open modal
   */
  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    window.addEventListener("open-shortcuts-modal", handleOpen);
    return () => window.removeEventListener("open-shortcuts-modal", handleOpen);
  }, []);

  /**
   * Handle Escape key to close
   */
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
        setSearchQuery("");
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen]);

  /**
   * Filter shortcuts by search query
   */
  const filteredShortcuts = ALL_SHORTCUTS.filter((shortcut) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      shortcut.description.toLowerCase().includes(query) ||
      shortcut.keys.toLowerCase().includes(query) ||
      shortcut.category.toLowerCase().includes(query)
    );
  });

  /**
   * Group filtered shortcuts by category
   */
  const groupedShortcuts: Record<string, ShortcutConfig[]> = {
    global: filteredShortcuts.filter((s) => s.category === "global"),
    navigation: filteredShortcuts.filter((s) => s.category === "navigation"),
    "page-actions": filteredShortcuts.filter((s) => s.category === "page-actions"),
    editing: filteredShortcuts.filter((s) => s.category === "editing"),
  };

  /**
   * Render shortcut row
   */
  const renderShortcut = (shortcut: ShortcutConfig) => {
    const keys = formatKeys(shortcut.keys);
    return (
      <div
        key={shortcut.id}
        className="flex items-center justify-between py-3 px-4 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
      >
        <div className="flex-1">
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {shortcut.description}
          </div>
          {shortcut.scope && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Available on {shortcut.scope} page
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">
          {keys.split("+").map((key, idx) => (
            <span key={idx} className="flex items-center gap-1">
              <Kbd>{key.trim()}</Kbd>
              {idx < keys.split("+").length - 1 && (
                <span className="text-gray-400 text-xs">+</span>
              )}
            </span>
          ))}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[9998] bg-black/50 backdrop-blur-sm"
        onClick={() => {
          setIsOpen(false);
          setSearchQuery("");
        }}
      />

      {/* Modal */}
      <div className="fixed top-[10%] left-1/2 -translate-x-1/2 z-[9999] w-full max-w-3xl glass-card border-2 border-gray-200 dark:border-gray-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={() => {
              setIsOpen(false);
              setSearchQuery("");
            }}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Close shortcuts modal"
          >
            <X size={20} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search shortcuts..."
              className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              autoFocus
            />
          </div>
        </div>

        {/* Shortcuts List */}
        <div className="max-h-[500px] overflow-y-auto p-6 space-y-6">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => {
            if (shortcuts.length === 0) return null;

            const categoryTitle = {
              global: "Global",
              navigation: "Navigation",
              "page-actions": "Page Actions",
              editing: "Editing",
            }[category];

            return (
              <div key={category}>
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                  {categoryTitle}
                </h3>
                <div className="space-y-1">
                  {shortcuts.map((shortcut) => renderShortcut(shortcut))}
                </div>
              </div>
            );
          })}

          {filteredShortcuts.length === 0 && (
            <div className="py-12 text-center text-gray-500 dark:text-gray-400">
              No shortcuts found for &quot;{searchQuery}&quot;
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>
              Press <Kbd>Esc</Kbd> to close
            </span>
            <span>{filteredShortcuts.length} shortcuts available</span>
          </div>
        </div>
      </div>
    </>
  );
}
