/**
 * Keyboard Shortcuts Registry
 *
 * Centralized configuration for all keyboard shortcuts in the application.
 * Used by:
 * - CommandPalette component (search results)
 * - useKeyboardShortcuts hook (registrations)
 * - ShortcutsModal component (help display)
 *
 * Reference: Story 6 AC-2 (Keyboard Shortcuts System)
 */

export interface ShortcutConfig {
  /** Unique identifier for the shortcut */
  id: string;
  /** Keys to press (e.g., 'ctrl+k', 'g>d' for sequences) */
  keys: string;
  /** Human-readable description */
  description: string;
  /** Category for grouping in help modal */
  category: 'global' | 'navigation' | 'page-actions' | 'editing';
  /** Where the shortcut is active (undefined = everywhere) */
  scope?: string;
  /** Action to execute (for useKeyboardShortcuts) */
  action?: () => void;
}

/**
 * Global keyboard shortcuts
 *
 * These shortcuts work everywhere in the application
 */
export const GLOBAL_SHORTCUTS: ShortcutConfig[] = [
  {
    id: 'open-command-palette',
    keys: 'mod+k',
    description: 'Open command palette',
    category: 'global',
  },
  {
    id: 'toggle-sidebar',
    keys: 'mod+b',
    description: 'Toggle sidebar',
    category: 'global',
  },
  {
    id: 'focus-search',
    keys: '/',
    description: 'Focus global search',
    category: 'global',
  },
  {
    id: 'toggle-theme',
    keys: 'mod+shift+d',
    description: 'Toggle dark/light mode',
    category: 'global',
  },
  {
    id: 'show-shortcuts',
    keys: '?',
    description: 'Show keyboard shortcuts help',
    category: 'global',
  },
  {
    id: 'close-modal',
    keys: 'escape',
    description: 'Close any open modal/dropdown',
    category: 'global',
  },
];

/**
 * Navigation shortcuts (vim-style with 'g' prefix)
 *
 * Sequence shortcuts with 'g' then another key
 */
export const NAVIGATION_SHORTCUTS: ShortcutConfig[] = [
  {
    id: 'goto-dashboard',
    keys: 'g>d',
    description: 'Go to Dashboard',
    category: 'navigation',
  },
  {
    id: 'goto-agents',
    keys: 'g>a',
    description: 'Go to Agents',
    category: 'navigation',
  },
  {
    id: 'goto-executions',
    keys: 'g>e',
    description: 'Go to Executions',
    category: 'navigation',
  },
  {
    id: 'goto-queue',
    keys: 'g>q',
    description: 'Go to Queue',
    category: 'navigation',
  },
  {
    id: 'goto-settings',
    keys: 'g>s',
    description: 'Go to Settings',
    category: 'navigation',
  },
  {
    id: 'goto-tenants',
    keys: 'g>t',
    description: 'Go to Tenants',
    category: 'navigation',
  },
  {
    id: 'goto-providers',
    keys: 'g>p',
    description: 'Go to Providers',
    category: 'navigation',
  },
];

/**
 * Page-specific action shortcuts
 *
 * These shortcuts are scoped to specific pages
 */
export const PAGE_ACTION_SHORTCUTS: ShortcutConfig[] = [
  // Agents page
  {
    id: 'create-agent',
    keys: 'c',
    description: 'Create Agent',
    category: 'page-actions',
    scope: 'agents',
  },
  // Executions page
  {
    id: 'refresh-data',
    keys: 'r',
    description: 'Refresh data',
    category: 'page-actions',
    scope: 'executions',
  },
  {
    id: 'export-csv',
    keys: 'x',
    description: 'Export to CSV',
    category: 'page-actions',
    scope: 'executions',
  },
  // Queue page
  {
    id: 'pause-resume-queue',
    keys: 'p',
    description: 'Pause/Resume queue',
    category: 'page-actions',
    scope: 'queue',
  },
];

/**
 * Combined shortcuts registry
 *
 * Used by ShortcutsModal for displaying all shortcuts
 */
export const ALL_SHORTCUTS: ShortcutConfig[] = [
  ...GLOBAL_SHORTCUTS,
  ...NAVIGATION_SHORTCUTS,
  ...PAGE_ACTION_SHORTCUTS,
];

/**
 * Get shortcuts by category
 */
export function getShortcutsByCategory(category: ShortcutConfig['category']): ShortcutConfig[] {
  return ALL_SHORTCUTS.filter((s) => s.category === category);
}

/**
 * Get shortcut by ID
 */
export function getShortcutById(id: string): ShortcutConfig | undefined {
  return ALL_SHORTCUTS.find((s) => s.id === id);
}

/**
 * Get shortcuts by scope
 */
export function getShortcutsByScope(scope?: string): ShortcutConfig[] {
  return ALL_SHORTCUTS.filter((s) => s.scope === scope || s.scope === undefined);
}

/**
 * Format keys for display (replace 'mod' with platform-specific key)
 */
export function formatKeys(keys: string): string {
  const isMac = typeof window !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const formatted = keys
    .replace(/mod/g, isMac ? '⌘' : 'Ctrl')
    .replace(/shift/g, isMac ? '⇧' : 'Shift')
    .replace(/alt/g, isMac ? '⌥' : 'Alt')
    .replace(/>/g, ' then ');

  return formatted
    .split(/[\+\s]/)
    .map((key) => key.charAt(0).toUpperCase() + key.slice(1))
    .join(isMac ? '' : '+');
}
