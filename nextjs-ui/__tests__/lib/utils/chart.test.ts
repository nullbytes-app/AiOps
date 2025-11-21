import {
  formatChartTimestamp,
  formatTooltipTimestamp,
  autoSelectGranularity,
  transformTrendData,
} from '@/lib/utils/chart';
import type { AgentTrendDataPoint } from '@/types/agent-performance';

describe('chart utilities', () => {
  describe('formatChartTimestamp', () => {
    it('formats hourly timestamps with hour notation', () => {
      const timestamp = '2025-01-14T14:00:00Z';
      const result = formatChartTimestamp(timestamp, 'hourly');
      // Check pattern (timezone may vary): "MMM d, ha" → "Jan 14, 2pm" or "Jan 14, 7PM"
      expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}, \d{1,2}[AP]M$/);
      expect(result).toContain('Jan 14');
    });

    it('formats daily timestamps without hour', () => {
      const timestamp = '2025-01-14T00:00:00Z';
      const result = formatChartTimestamp(timestamp, 'daily');
      expect(result).toBe('Jan 14');
    });
  });

  describe('formatTooltipTimestamp', () => {
    it('formats with full date and time', () => {
      const timestamp = '2025-01-14T14:00:00Z';
      const result = formatTooltipTimestamp(timestamp);
      // Note: Result may vary by timezone, so we check for expected components
      expect(result).toContain('Jan');
      expect(result).toContain('14');
      expect(result).toContain('2025');
      expect(result).toContain('PM');
    });
  });

  describe('autoSelectGranularity', () => {
    it('returns "hourly" for date range < 7 days', () => {
      const startDate = '2025-01-14';
      const endDate = '2025-01-20'; // 6 days
      const result = autoSelectGranularity(startDate, endDate);
      expect(result).toBe('hourly');
    });

    it('returns "daily" for date range >= 7 days', () => {
      const startDate = '2025-01-14';
      const endDate = '2025-01-21'; // 7 days
      const result = autoSelectGranularity(startDate, endDate);
      expect(result).toBe('daily');
    });

    it('returns "daily" for date range > 7 days', () => {
      const startDate = '2025-01-01';
      const endDate = '2025-01-31'; // 30 days
      const result = autoSelectGranularity(startDate, endDate);
      expect(result).toBe('daily');
    });
  });

  describe('transformTrendData', () => {
    it('converts avg_execution_time_ms to avg_execution_time_s', () => {
      const dataPoints: AgentTrendDataPoint[] = [
        {
          timestamp: '2025-01-14T00:00:00Z',
          execution_count: 45,
          avg_execution_time_ms: 2345.67,
          p50_execution_time_ms: 1890.0,
          p95_execution_time_ms: 4567.89,
        },
        {
          timestamp: '2025-01-14T01:00:00Z',
          execution_count: 52,
          avg_execution_time_ms: 2123.45,
          p50_execution_time_ms: 1780.0,
          p95_execution_time_ms: 4234.56,
        },
      ];

      const result = transformTrendData(dataPoints);

      expect(result).toHaveLength(2);
      // Use toBeCloseTo for floating point comparisons (handles precision issues)
      expect(result[0].avg_execution_time_s).toBeCloseTo(2.34567, 5);
      expect(result[1].avg_execution_time_s).toBeCloseTo(2.12345, 5);
      // Original fields should still exist
      expect(result[0].execution_count).toBe(45);
      expect(result[0].avg_execution_time_ms).toBe(2345.67);
    });

    it('handles empty array', () => {
      const result = transformTrendData([]);
      expect(result).toEqual([]);
    });
  });
});
