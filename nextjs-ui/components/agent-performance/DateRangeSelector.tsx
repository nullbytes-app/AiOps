/**
 * Date Range Selector Component
 * Tabs for preset date ranges (Last 7/30 days, Custom)
 * Following 2025 shadcn/ui Tabs patterns
 */

'use client';

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getDateRangePreset } from '@/lib/utils/performance';

type DateRangePreset = 'last_7' | 'last_30' | 'custom';

interface DateRangeSelectorProps {
  value: DateRangePreset;
  onChange: (preset: DateRangePreset) => void;
  onDateChange?: (startDate: string, endDate: string) => void;
}

export function DateRangeSelector({ value, onChange, onDateChange }: DateRangeSelectorProps) {
  const handlePresetChange = (preset: DateRangePreset) => {
    onChange(preset);

    if (preset !== 'custom' && onDateChange) {
      const { start, end } = getDateRangePreset(preset);
      onDateChange(start, end);
    }
  };

  return (
    <Tabs value={value} onValueChange={(v) => handlePresetChange(v as DateRangePreset)}>
      <TabsList>
        <TabsTrigger value="last_7">Last 7 days</TabsTrigger>
        <TabsTrigger value="last_30">Last 30 days</TabsTrigger>
        <TabsTrigger value="custom" disabled>Custom</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}