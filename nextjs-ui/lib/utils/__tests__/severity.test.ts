/**
 * Unit Tests for Severity Utilities
 * Story 15: Agent Performance Dashboard - Error Analysis
 * Testing AC #3: Severity calculation and badge colors
 */

import { getSeverityLevel, getSeverityColor, getSeverityLabel } from '../severity';

describe('getSeverityLevel', () => {
  it('returns "low" for occurrences < 5', () => {
    expect(getSeverityLevel(0)).toBe('low');
    expect(getSeverityLevel(1)).toBe('low');
    expect(getSeverityLevel(4)).toBe('low');
  });

  it('returns "medium" for occurrences between 5 and 20', () => {
    expect(getSeverityLevel(5)).toBe('medium');
    expect(getSeverityLevel(10)).toBe('medium');
    expect(getSeverityLevel(20)).toBe('medium');
  });

  it('returns "high" for occurrences > 20', () => {
    expect(getSeverityLevel(21)).toBe('high');
    expect(getSeverityLevel(50)).toBe('high');
    expect(getSeverityLevel(100)).toBe('high');
  });

  it('handles edge cases correctly', () => {
    expect(getSeverityLevel(4)).toBe('low'); // boundary: just below medium
    expect(getSeverityLevel(5)).toBe('medium'); // boundary: start of medium
    expect(getSeverityLevel(20)).toBe('medium'); // boundary: end of medium
    expect(getSeverityLevel(21)).toBe('high'); // boundary: start of high
  });
});

describe('getSeverityColor', () => {
  it('returns gray classes for low severity', () => {
    const colorClasses = getSeverityColor('low');
    expect(colorClasses).toContain('bg-gray-100');
    expect(colorClasses).toContain('text-gray-700');
    expect(colorClasses).toContain('border-gray-300');
  });

  it('returns yellow classes for medium severity', () => {
    const colorClasses = getSeverityColor('medium');
    expect(colorClasses).toContain('bg-yellow-100');
    expect(colorClasses).toContain('text-yellow-700');
    expect(colorClasses).toContain('border-yellow-300');
  });

  it('returns red classes for high severity', () => {
    const colorClasses = getSeverityColor('high');
    expect(colorClasses).toContain('bg-red-100');
    expect(colorClasses).toContain('text-red-700');
    expect(colorClasses).toContain('border-red-300');
  });
});

describe('getSeverityLabel', () => {
  it('returns accessible label for low severity', () => {
    expect(getSeverityLabel('low')).toBe('Low severity');
  });

  it('returns accessible label for medium severity', () => {
    expect(getSeverityLabel('medium')).toBe('Medium severity');
  });

  it('returns accessible label for high severity', () => {
    expect(getSeverityLabel('high')).toBe('High severity');
  });
});
