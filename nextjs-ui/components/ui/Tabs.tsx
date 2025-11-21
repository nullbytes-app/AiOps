import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react';
import { ReactNode } from 'react';

export interface TabItem {
  /**
   * Unique key for the tab
   */
  key: string;
  /**
   * Tab label (shown in the tab button)
   */
  label: string;
  /**
   * Tab content (shown when tab is active)
   */
  content: ReactNode;
  /**
   * Optional icon to display before the label
   */
  icon?: ReactNode;
  /**
   * Disable this specific tab
   */
  disabled?: boolean;
}

export interface TabsProps {
  /**
   * Array of tab items to render
   */
  tabs: TabItem[];
  /**
   * Default selected tab index (0-based)
   */
  defaultIndex?: number;
  /**
   * Controlled selected tab index (0-based)
   */
  selectedIndex?: number;
  /**
   * Callback when tab changes
   */
  onChange?: (index: number) => void;
  /**
   * Variant: 'pills' (rounded tabs), 'underline' (border-bottom tabs), 'boxed' (bordered tabs)
   */
  variant?: 'pills' | 'underline' | 'boxed';
  /**
   * Full width tabs (each tab takes equal space)
   */
  fullWidth?: boolean;
  /**
   * Additional CSS classes for the tab group container
   */
  className?: string;
}

const variantClasses = {
  pills: {
    list: 'bg-gray-100 dark:bg-gray-800 p-1 rounded-xl space-x-1',
    tab: (selected: boolean) =>
      `rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
        selected
          ? 'bg-white dark:bg-gray-700 text-blue-700 dark:text-blue-400 shadow'
          : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50'
      }`,
  },
  underline: {
    list: 'border-b border-gray-200 dark:border-gray-700 space-x-4',
    tab: (selected: boolean) =>
      `px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
        selected
          ? 'border-blue-500 text-blue-700 dark:text-blue-400'
          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
      }`,
  },
  boxed: {
    list: 'bg-gray-50 dark:bg-gray-900 p-1 rounded-lg space-x-1 border border-gray-200 dark:border-gray-700',
    tab: (selected: boolean) =>
      `rounded-md px-4 py-2 text-sm font-medium transition-all ${
        selected
          ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm border border-gray-200 dark:border-gray-700'
          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
      }`,
  },
};

/**
 * Tabs component using Headless UI
 *
 * Features:
 * - Keyboard navigation (Arrow keys, Home, End)
 * - Accessible (ARIA labels, roles, keyboard support)
 * - 3 style variants (pills, underline, boxed)
 * - Controlled and uncontrolled modes
 * - Optional icons
 * - Full-width layout option
 * - Disabled tabs support
 *
 * @example
 * ```tsx
 * const tabs = [
 *   { key: 'overview', label: 'Overview', content: <p>Overview content</p> },
 *   { key: 'details', label: 'Details', content: <p>Details content</p> },
 *   { key: 'settings', label: 'Settings', content: <p>Settings content</p> },
 * ];
 *
 * <Tabs tabs={tabs} variant="pills" onChange={(idx) => console.log(idx)} />
 * ```
 */
export function Tabs({
  tabs,
  defaultIndex = 0,
  selectedIndex,
  onChange,
  variant = 'pills',
  fullWidth = false,
  className = '',
}: TabsProps) {
  const classes = variantClasses[variant];

  return (
    <div className={`w-full ${className}`}>
      <TabGroup
        defaultIndex={defaultIndex}
        selectedIndex={selectedIndex}
        onChange={onChange}
      >
        <TabList className={`flex ${fullWidth ? '' : 'inline-flex'} ${classes.list}`}>
          {tabs.map((tab) => (
            <Tab
              key={tab.key}
              disabled={tab.disabled}
              className={({ selected }) =>
                `${classes.tab(selected)} ${
                  fullWidth ? 'flex-1' : ''
                } ${
                  tab.disabled
                    ? 'opacity-50 cursor-not-allowed'
                    : 'cursor-pointer focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2'
                }`
              }
            >
              {() => (
                <span className="flex items-center justify-center gap-2">
                  {tab.icon && <span className="flex-shrink-0">{tab.icon}</span>}
                  <span>{tab.label}</span>
                </span>
              )}
            </Tab>
          ))}
        </TabList>

        <TabPanels className="mt-4">
          {tabs.map((tab) => (
            <TabPanel
              key={tab.key}
              className="rounded-lg glass-card p-4 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {tab.content}
            </TabPanel>
          ))}
        </TabPanels>
      </TabGroup>
    </div>
  );
}
