/**
 * Unit tests for performance utility functions
 * Story 16: Tests for getDurationSeverity, getDurationColor, formatExecutionTimeLong
 * Coverage target: 100%
 */

import {
  formatExecutionTime,
  formatCount,
  getSuccessRateColor,
  getDateRangePreset,
  getDurationSeverity,
  getDurationColor,
  formatExecutionTimeLong,
} from '@/lib/utils/performance';

describe('formatExecutionTime', () => {
  it('formats time < 1000ms as milliseconds', () => {
    expect(formatExecutionTime(0)).toBe('0ms');
    expect(formatExecutionTime(450)).toBe('450ms');
    expect(formatExecutionTime(999)).toBe('999ms');
  });

  it('formats time >= 1000ms as seconds with 2 decimals', () => {
    expect(formatExecutionTime(1000)).toBe('1.00s');
    expect(formatExecutionTime(2345)).toBe('2.35s');
    expect(formatExecutionTime(125000)).toBe('125.00s');
  });

  it('rounds milliseconds to nearest integer', () => {
    expect(formatExecutionTime(450.6)).toBe('451ms');
    expect(formatExecutionTime(999.4)).toBe('999ms');
  });
});

describe('formatCount', () => {
  it('formats counts < 1000 as plain numbers', () => {
    expect(formatCount(0)).toBe('0');
    expect(formatCount(450)).toBe('450');
    expect(formatCount(999)).toBe('999');
  });

  it('formats counts >= 1000 and < 1M with K notation (1 decimal)', () => {
    expect(formatCount(1000)).toBe('1.0K');
    expect(formatCount(1234)).toBe('1.2K');
    expect(formatCount(999999)).toBe('1000.0K');
  });

  it('formats counts >= 1M with M notation (1 decimal)', () => {
    expect(formatCount(1000000)).toBe('1.0M');
    expect(formatCount(1500000)).toBe('1.5M');
    expect(formatCount(12345678)).toBe('12.3M');
  });
});

describe('getSuccessRateColor', () => {
  it('returns green for success rate >= 95%', () => {
    const result95 = getSuccessRateColor(95);
    expect(result95.color).toBe('text-green-600');
    expect(result95.variant).toBe('success');

    const result99 = getSuccessRateColor(99);
    expect(result99.color).toBe('text-green-600');
    expect(result99.variant).toBe('success');

    const result100 = getSuccessRateColor(100);
    expect(result100.color).toBe('text-green-600');
    expect(result100.variant).toBe('success');
  });

  it('returns yellow for success rate 85-94.9%', () => {
    const result85 = getSuccessRateColor(85);
    expect(result85.color).toBe('text-yellow-600');
    expect(result85.variant).toBe('warning');

    const result90 = getSuccessRateColor(90);
    expect(result90.color).toBe('text-yellow-600');
    expect(result90.variant).toBe('warning');

    const result94_9 = getSuccessRateColor(94.9);
    expect(result94_9.color).toBe('text-yellow-600');
    expect(result94_9.variant).toBe('warning');
  });

  it('returns red for success rate < 85%', () => {
    const result0 = getSuccessRateColor(0);
    expect(result0.color).toBe('text-red-600');
    expect(result0.variant).toBe('destructive');

    const result50 = getSuccessRateColor(50);
    expect(result50.color).toBe('text-red-600');
    expect(result50.variant).toBe('destructive');

    const result84_9 = getSuccessRateColor(84.9);
    expect(result84_9.color).toBe('text-red-600');
    expect(result84_9.variant).toBe('destructive');
  });
});

describe('getDateRangePreset', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2025-01-21T12:00:00Z'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns correct range for last_7 preset', () => {
    const result = getDateRangePreset('last_7');
    expect(result.start).toBe('2025-01-14');
    expect(result.end).toBe('2025-01-21');
  });

  it('returns correct range for last_30 preset', () => {
    const result = getDateRangePreset('last_30');
    expect(result.start).toBe('2024-12-22');
    expect(result.end).toBe('2025-01-21');
  });

  it('returns current date for custom preset', () => {
    const result = getDateRangePreset('custom');
    expect(result.start).toBe('2025-01-21');
    expect(result.end).toBe('2025-01-21');
  });
});

// Story 16 AC #3: Duration severity and color coding tests
describe('getDurationSeverity', () => {
  it('returns "normal" for durations < 30 seconds', () => {
    expect(getDurationSeverity(0)).toBe('normal');
    expect(getDurationSeverity(1000)).toBe('normal'); // 1s
    expect(getDurationSeverity(15000)).toBe('normal'); // 15s
    expect(getDurationSeverity(29999)).toBe('normal'); // 29.999s
  });

  it('returns "warning" for durations between 30-60 seconds (inclusive)', () => {
    expect(getDurationSeverity(30000)).toBe('warning'); // 30s exactly
    expect(getDurationSeverity(45000)).toBe('warning'); // 45s
    expect(getDurationSeverity(60000)).toBe('warning'); // 60s exactly
  });

  it('returns "slow" for durations > 60 seconds', () => {
    expect(getDurationSeverity(60001)).toBe('slow'); // 60.001s
    expect(getDurationSeverity(90000)).toBe('slow'); // 90s
    expect(getDurationSeverity(120000)).toBe('slow'); // 2 minutes
    expect(getDurationSeverity(300000)).toBe('slow'); // 5 minutes
  });

  it('handles edge cases at exact boundaries', () => {
    expect(getDurationSeverity(29999)).toBe('normal'); // Just under 30s
    expect(getDurationSeverity(30000)).toBe('warning'); // Exactly 30s
    expect(getDurationSeverity(60000)).toBe('warning'); // Exactly 60s
    expect(getDurationSeverity(60001)).toBe('slow'); // Just over 60s
  });
});

describe('getDurationColor', () => {
  it('returns foreground color for normal severity', () => {
    expect(getDurationColor('normal')).toBe('text-foreground');
  });

  it('returns warning color for warning severity', () => {
    expect(getDurationColor('warning')).toBe('text-warning-600');
  });

  it('returns destructive color for slow severity', () => {
    expect(getDurationColor('slow')).toBe('text-destructive');
  });
});

// Story 16 AC #1: Duration formatting tests
describe('formatExecutionTimeLong', () => {
  it('formats durations < 60 seconds with seconds and 2 decimal places', () => {
    expect(formatExecutionTimeLong(450)).toBe('0.45s');
    expect(formatExecutionTimeLong(1000)).toBe('1.00s');
    expect(formatExecutionTimeLong(15230)).toBe('15.23s');
    expect(formatExecutionTimeLong(45678)).toBe('45.68s');
    expect(formatExecutionTimeLong(59999)).toBe('60.00s');
  });

  it('formats durations >= 60 seconds with minutes and seconds', () => {
    expect(formatExecutionTimeLong(60000)).toBe('1m 0s'); // Exactly 1 minute
    expect(formatExecutionTimeLong(75000)).toBe('1m 15s'); // 1m 15s
    expect(formatExecutionTimeLong(120000)).toBe('2m 0s'); // Exactly 2 minutes
    expect(formatExecutionTimeLong(145230)).toBe('2m 25s'); // 2m 25.23s -> 2m 25s (floors seconds)
    expect(formatExecutionTimeLong(359999)).toBe('5m 59s'); // 5m 59.999s -> 5m 59s
  });

  it('formats very long durations correctly', () => {
    expect(formatExecutionTimeLong(600000)).toBe('10m 0s'); // 10 minutes
    expect(formatExecutionTimeLong(3600000)).toBe('60m 0s'); // 1 hour (shown as 60m)
    expect(formatExecutionTimeLong(3665000)).toBe('61m 5s'); // 1 hour 1m 5s
  });

  it('handles edge cases', () => {
    expect(formatExecutionTimeLong(0)).toBe('0.00s');
    expect(formatExecutionTimeLong(1)).toBe('0.00s'); // 1ms rounds to 0.00s
    expect(formatExecutionTimeLong(59500)).toBe('59.50s'); // Just under 1 minute
    expect(formatExecutionTimeLong(59999)).toBe('60.00s'); // 59.999s rounds to 60.00s
  });

  it('floors the seconds when formatting minutes', () => {
    expect(formatExecutionTimeLong(75999)).toBe('1m 15s'); // 1m 15.999s -> 1m 15s
    expect(formatExecutionTimeLong(145678)).toBe('2m 25s'); // 2m 25.678s -> 2m 25s
  });
});

// Integration test: severity and color work together
describe('duration severity with color coding integration', () => {
  it('correctly categorizes and colors a fast execution', () => {
    const durationMs = 15000; // 15 seconds
    const severity = getDurationSeverity(durationMs);
    const color = getDurationColor(severity);
    const formatted = formatExecutionTimeLong(durationMs);

    expect(severity).toBe('normal');
    expect(color).toBe('text-foreground');
    expect(formatted).toBe('15.00s');
  });

  it('correctly categorizes and colors a moderate execution', () => {
    const durationMs = 45000; // 45 seconds
    const severity = getDurationSeverity(durationMs);
    const color = getDurationColor(severity);
    const formatted = formatExecutionTimeLong(durationMs);

    expect(severity).toBe('warning');
    expect(color).toBe('text-warning-600');
    expect(formatted).toBe('45.00s');
  });

  it('correctly categorizes and colors a slow execution', () => {
    const durationMs = 145000; // 2m 25s
    const severity = getDurationSeverity(durationMs);
    const color = getDurationColor(severity);
    const formatted = formatExecutionTimeLong(durationMs);

    expect(severity).toBe('slow');
    expect(color).toBe('text-destructive');
    expect(formatted).toBe('2m 25s');
  });
});
