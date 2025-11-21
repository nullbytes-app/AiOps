/**
 * Unit Tests for BudgetProgressBar Component
 *
 * Tests color-coded progress bars with over-budget indicators
 * Maps to Story: nextjs-story-12-llm-cost-dashboard-budget-bars
 */

import { render, screen } from "@testing-library/react";
import { BudgetProgressBar } from "@/components/costs/BudgetProgressBar";

describe("BudgetProgressBar", () => {
  describe("Rendering", () => {
    it("should render progress bar with correct structure", () => {
      render(
        <BudgetProgressBar
          utilized={50}
          budget={1000}
          spent={500}
        />
      );

      // Should render spent and budget text
      expect(screen.getByText(/\$500\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$1,000\.00/)).toBeInTheDocument();
    });

    it("should render progress bar for null budget (no budget configured)", () => {
      render(
        <BudgetProgressBar
          utilized={0}
          budget={null}
          spent={500}
        />
      );

      // When budget is null, component shows "No budget configured" text, not spent amount
      expect(screen.getByText(/No budget configured/)).toBeInTheDocument();
    });
  });

  describe("Color Coding", () => {
    it("should apply success color for < 75% utilization", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={50}
          budget={1000}
          spent={500}
        />
      );

      const progressIndicator = container.querySelector('[role="progressbar"] > div');
      expect(progressIndicator).toHaveClass("bg-green-500");
    });

    it("should apply warning color for 75-89% utilization", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={80}
          budget={1000}
          spent={800}
        />
      );

      const progressIndicator = container.querySelector('[role="progressbar"] > div');
      expect(progressIndicator).toHaveClass("bg-yellow-500");
    });

    it("should apply destructive color for >= 90% utilization", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={95}
          budget={1000}
          spent={950}
        />
      );

      const progressIndicator = container.querySelector('[role="progressbar"] > div');
      expect(progressIndicator).toHaveClass("bg-red-500");
    });

    it("should apply neutral color for 0% utilization with null budget", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={0}
          budget={null}
          spent={500}
        />
      );

      const progressIndicator = container.querySelector('[role="progressbar"] > div');
      expect(progressIndicator).toHaveClass("bg-gray-300");
    });
  });

  describe("Over Budget Indicator", () => {
    it("should show warning icon for > 100% utilization", () => {
      render(
        <BudgetProgressBar
          utilized={120}
          budget={1000}
          spent={1200}
        />
      );

      expect(screen.getByText(/⚠️ Over budget!/)).toBeInTheDocument();
    });

    it("should NOT show warning icon for <= 100% utilization", () => {
      render(
        <BudgetProgressBar
          utilized={95}
          budget={1000}
          spent={950}
        />
      );

      expect(screen.queryByText(/⚠️ Over budget!/)).not.toBeInTheDocument();
    });

    it("should cap visual progress at 100% for over budget", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={150}
          budget={1000}
          spent={1500}
        />
      );

      // Progress bar should be at 100% width, not 150%
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toHaveAttribute("aria-valuenow", "100");
    });
  });

  describe("Percentage Display", () => {
    it("should display utilization percentage for valid budget", () => {
      render(
        <BudgetProgressBar
          utilized={75.5}
          budget={1000}
          spent={755}
        />
      );

      expect(screen.getByText(/75\.5% utilized/)).toBeInTheDocument();
    });

    it("should display 0.0% for zero utilization", () => {
      render(
        <BudgetProgressBar
          utilized={0}
          budget={null}
          spent={500}
        />
      );

      expect(screen.getByText(/0\.0% utilized/)).toBeInTheDocument();
    });

    it("should format percentage to 1 decimal place", () => {
      render(
        <BudgetProgressBar
          utilized={33.333333}
          budget={1000}
          spent={333.33}
        />
      );

      expect(screen.getByText(/33\.3% utilized/)).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle 0% utilization", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={0}
          budget={1000}
          spent={0}
        />
      );

      expect(screen.getByText(/0\.0% utilized/)).toBeInTheDocument();
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toHaveAttribute("aria-valuenow", "0");
    });

    it("should handle exactly 100% utilization", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={100}
          budget={1000}
          spent={1000}
        />
      );

      expect(screen.getByText(/100\.0% utilized/)).toBeInTheDocument();
      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toHaveAttribute("aria-valuenow", "100");
    });

    it("should handle very small budgets", () => {
      render(
        <BudgetProgressBar
          utilized={50}
          budget={10}
          spent={5}
        />
      );

      expect(screen.getByText(/\$10\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$5\.00/)).toBeInTheDocument();
    });

    it("should handle very large budgets", () => {
      render(
        <BudgetProgressBar
          utilized={50}
          budget={1000000}
          spent={500000}
        />
      );

      expect(screen.getByText(/\$1,000,000\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$500,000\.00/)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA attributes", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={75}
          budget={1000}
          spent={750}
        />
      );

      const progressBar = container.querySelector('[role="progressbar"]');
      expect(progressBar).toHaveAttribute("role", "progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow");
      expect(progressBar).toHaveAttribute("aria-valuemin", "0");
      expect(progressBar).toHaveAttribute("aria-valuemax", "100");
    });

    it("should have descriptive aria-label", () => {
      const { container } = render(
        <BudgetProgressBar
          utilized={75}
          budget={1000}
          spent={750}
        />
      );

      const progressBar = container.querySelector('[role="progressbar"]');
      const ariaLabel = progressBar?.getAttribute("aria-label");
      expect(ariaLabel).toBe("Budget utilization: 75.0%");
    });
  });
});
