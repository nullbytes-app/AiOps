/**
 * Unit tests for formatting utilities
 * Tests currency, large number, and percentage formatting
 */

import {
  formatCurrency,
  formatLargeNumber,
  formatPercentageChange,
  formatPercentage,
} from './formatters';

describe('formatCurrency', () => {
  test('formats currency with 2 decimal places', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56');
  });

  test('formats currency with trailing zeros', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50');
  });

  test('formats zero as currency', () => {
    expect(formatCurrency(0)).toBe('$0.00');
  });

  test('formats large numbers with commas', () => {
    expect(formatCurrency(1234567.89)).toBe('$1,234,567.89');
  });

  test('formats small decimals correctly', () => {
    expect(formatCurrency(0.01)).toBe('$0.01');
    expect(formatCurrency(0.99)).toBe('$0.99');
  });

  test('handles negative numbers', () => {
    expect(formatCurrency(-1234.56)).toBe('-$1,234.56');
  });
});

describe('formatLargeNumber', () => {
  test('formats numbers under 1000 without suffix', () => {
    expect(formatLargeNumber(999)).toBe('999');
    expect(formatLargeNumber(500)).toBe('500');
    expect(formatLargeNumber(0)).toBe('0');
  });

  test('formats thousands with K suffix', () => {
    expect(formatLargeNumber(1234)).toBe('1.2K');
    expect(formatLargeNumber(1500)).toBe('1.5K');
    expect(formatLargeNumber(999999)).toBe('1000.0K');
  });

  test('formats millions with M suffix', () => {
    expect(formatLargeNumber(1234567)).toBe('1.2M');
    expect(formatLargeNumber(1500000)).toBe('1.5M');
    expect(formatLargeNumber(10000000)).toBe('10.0M');
  });

  test('rounds to 1 decimal place', () => {
    expect(formatLargeNumber(1234)).toBe('1.2K');
    expect(formatLargeNumber(1567)).toBe('1.6K');
  });
});

describe('formatPercentageChange', () => {
  test('calculates positive change correctly', () => {
    const result = formatPercentageChange(115, 100);
    expect(result.value).toBe(15);
    expect(result.formatted).toBe('+15.0%');
    expect(result.icon).toBe('↑');
    expect(result.isPositive).toBe(true);
  });

  test('calculates negative change correctly', () => {
    const result = formatPercentageChange(90, 100);
    expect(result.value).toBe(-10);
    expect(result.formatted).toBe('10.0%');
    expect(result.icon).toBe('↓');
    expect(result.isPositive).toBe(false);
  });

  test('handles zero change', () => {
    const result = formatPercentageChange(100, 100);
    expect(result.value).toBe(0);
    expect(result.formatted).toBe('0.0%');
    expect(result.icon).toBe('→');
    expect(result.isPositive).toBeNull();
  });

  test('handles division by zero', () => {
    const result = formatPercentageChange(100, 0);
    expect(result.value).toBe(0);
    expect(result.formatted).toBe('N/A');
    expect(result.icon).toBe('→');
    expect(result.isPositive).toBeNull();
  });

  test('formats large percentage changes', () => {
    const result = formatPercentageChange(200, 100);
    expect(result.value).toBe(100);
    expect(result.formatted).toBe('+100.0%');
  });

  test('formats small percentage changes', () => {
    const result = formatPercentageChange(100.5, 100);
    expect(result.value).toBe(0.5);
    expect(result.formatted).toBe('+0.5%');
  });
});

describe('formatPercentage', () => {
  test('formats percentage with 1 decimal place', () => {
    expect(formatPercentage(85.5)).toBe('85.5%');
  });

  test('formats whole numbers with decimal', () => {
    expect(formatPercentage(100)).toBe('100.0%');
    expect(formatPercentage(0)).toBe('0.0%');
  });

  test('rounds to 1 decimal place', () => {
    expect(formatPercentage(85.56)).toBe('85.6%');
    expect(formatPercentage(85.54)).toBe('85.5%');
  });
});
