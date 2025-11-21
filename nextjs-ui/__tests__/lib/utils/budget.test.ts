/**
 * Unit Tests for Budget Utility Functions
 *
 * Tests color logic, currency formatting, and budget calculations
 * Maps to Story: nextjs-story-12-llm-cost-dashboard-budget-bars
 */

import {
  getBudgetColor,
  formatCurrency,
  calculateUtilization,
  isOverBudget,
} from "@/lib/utils/budget";

describe("Budget Utility Functions", () => {
  describe("getBudgetColor", () => {
    it("should return neutral color for null utilization", () => {
      const result = getBudgetColor(null);
      expect(result.variant).toBe("neutral");
      expect(result.color).toBe("text-gray-500");
    });

    it("should return neutral color for 0% utilization", () => {
      const result = getBudgetColor(0);
      expect(result.variant).toBe("neutral");
      expect(result.color).toBe("text-gray-500");
    });

    it("should return success color for < 75% utilization", () => {
      const result = getBudgetColor(50);
      expect(result.variant).toBe("success");
      expect(result.color).toBe("text-green-600");
    });

    it("should return success color for exactly 74.9% utilization", () => {
      const result = getBudgetColor(74.9);
      expect(result.variant).toBe("success");
      expect(result.color).toBe("text-green-600");
    });

    it("should return warning color for 75% utilization", () => {
      const result = getBudgetColor(75);
      expect(result.variant).toBe("warning");
      expect(result.color).toBe("text-yellow-600");
    });

    it("should return warning color for 75-89% utilization", () => {
      const result = getBudgetColor(82.5);
      expect(result.variant).toBe("warning");
      expect(result.color).toBe("text-yellow-600");
    });

    it("should return warning color for exactly 89.9% utilization", () => {
      const result = getBudgetColor(89.9);
      expect(result.variant).toBe("warning");
      expect(result.color).toBe("text-yellow-600");
    });

    it("should return destructive color for 90% utilization", () => {
      const result = getBudgetColor(90);
      expect(result.variant).toBe("destructive");
      expect(result.color).toBe("text-red-600");
    });

    it("should return destructive color for > 90% utilization", () => {
      const result = getBudgetColor(95);
      expect(result.variant).toBe("destructive");
      expect(result.color).toBe("text-red-600");
    });

    it("should return destructive color for 100%+ utilization", () => {
      const result = getBudgetColor(105);
      expect(result.variant).toBe("destructive");
      expect(result.color).toBe("text-red-600");
    });
  });

  describe("formatCurrency", () => {
    it("should format null as $0.00", () => {
      expect(formatCurrency(null)).toBe("$0.00");
    });

    it("should format 0 as $0.00", () => {
      expect(formatCurrency(0)).toBe("$0.00");
    });

    it("should format whole numbers with .00", () => {
      expect(formatCurrency(1000)).toBe("$1,000.00");
    });

    it("should format decimal numbers with 2 decimal places", () => {
      expect(formatCurrency(1234.56)).toBe("$1,234.56");
    });

    it("should round to 2 decimal places", () => {
      expect(formatCurrency(1234.567)).toBe("$1,234.57");
    });

    it("should format large numbers with comma separators", () => {
      expect(formatCurrency(1234567.89)).toBe("$1,234,567.89");
    });

    it("should format small decimal amounts correctly", () => {
      expect(formatCurrency(0.99)).toBe("$0.99");
    });

    it("should format negative amounts (edge case)", () => {
      expect(formatCurrency(-500.25)).toBe("-$500.25");
    });
  });

  describe("calculateUtilization", () => {
    it("should return null for null budget", () => {
      expect(calculateUtilization(500, null)).toBeNull();
    });

    it("should return null for 0 budget", () => {
      expect(calculateUtilization(500, 0)).toBeNull();
    });

    it("should return 0 for null spent", () => {
      expect(calculateUtilization(null, 1000)).toBe(0);
    });

    it("should return 0 for 0 spent", () => {
      expect(calculateUtilization(0, 1000)).toBe(0);
    });

    it("should calculate correct utilization percentage", () => {
      expect(calculateUtilization(500, 1000)).toBe(50);
    });

    it("should handle decimal results", () => {
      expect(calculateUtilization(333.33, 1000)).toBeCloseTo(33.333, 3);
    });

    it("should handle > 100% utilization", () => {
      expect(calculateUtilization(1200, 1000)).toBe(120);
    });

    it("should handle very small percentages", () => {
      expect(calculateUtilization(1, 1000)).toBe(0.1);
    });
  });

  describe("isOverBudget", () => {
    it("should return false for null budget", () => {
      expect(isOverBudget(500, null)).toBe(false);
    });

    it("should return false for 0 budget", () => {
      expect(isOverBudget(500, 0)).toBe(false);
    });

    it("should return false for null spent", () => {
      expect(isOverBudget(null, 1000)).toBe(false);
    });

    it("should return false for 0 spent", () => {
      expect(isOverBudget(0, 1000)).toBe(false);
    });

    it("should return false when spent < budget", () => {
      expect(isOverBudget(800, 1000)).toBe(false);
    });

    it("should return false when spent = budget", () => {
      expect(isOverBudget(1000, 1000)).toBe(false);
    });

    it("should return true when spent > budget", () => {
      expect(isOverBudget(1200, 1000)).toBe(true);
    });

    it("should return true when spent is just barely over", () => {
      expect(isOverBudget(1000.01, 1000)).toBe(true);
    });
  });
});
