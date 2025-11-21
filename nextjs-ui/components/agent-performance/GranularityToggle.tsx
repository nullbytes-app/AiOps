'use client';

import { Tab, TabGroup, TabList } from '@headlessui/react';
import type { TrendGranularity } from '@/types/agent-performance';

interface GranularityToggleProps {
  value: TrendGranularity;
  onChange: (value: TrendGranularity) => void;
}

const GRANULARITIES: TrendGranularity[] = ['hourly', 'daily'];

/**
 * Toggle between hourly and daily granularity for trend charts.
 */
export function GranularityToggle({
  value,
  onChange,
}: GranularityToggleProps) {
  const selectedIndex = GRANULARITIES.indexOf(value);

  const handleChange = (index: number) => {
    onChange(GRANULARITIES[index]);
  };

  return (
    <TabGroup selectedIndex={selectedIndex} onChange={handleChange}>
      <TabList className="flex inline-flex bg-gray-100 dark:bg-gray-800 p-1 rounded-xl space-x-1">
        {GRANULARITIES.map((granularity) => (
          <Tab
            key={granularity}
            className={({ selected }) =>
              `rounded-lg px-4 py-2.5 text-sm font-medium transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 ${
                selected
                  ? 'bg-white dark:bg-gray-700 text-blue-700 dark:text-blue-400 shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50'
              }`
            }
          >
            {granularity.charAt(0).toUpperCase() + granularity.slice(1)}
          </Tab>
        ))}
      </TabList>
    </TabGroup>
  );
}
