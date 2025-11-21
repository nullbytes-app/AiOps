/**
 * Unit tests for CustomTooltip component
 * Tests tooltip rendering, formatting, delta display, and color coding
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { CustomTooltip } from './CustomTooltip';
import { ChartDataPoint } from './DailySpendChart';

// Type for Recharts tooltip payload
interface TooltipPayload {
  value: number;
  payload: ChartDataPoint;
}

describe('CustomTooltip', () => {
  // Mock chart data point with increase (red)
  const mockDataPointIncrease: ChartDataPoint = {
    date: new Date('2025-01-15'),
    dateLabel: '01/15',
    amount: 1234.56,
    amountLabel: '$1,234.56',
    delta: 15.2,
    deltaLabel: '↑ 15.2%',
    deltaColor: 'red',
  };

  // Mock chart data point with decrease (green)
  const mockDataPointDecrease: ChartDataPoint = {
    date: new Date('2025-01-16'),
    dateLabel: '01/16',
    amount: 987.65,
    amountLabel: '$987.65',
    delta: -20.0,
    deltaLabel: '↓ 20.0%',
    deltaColor: 'green',
  };

  // Mock chart data point with no delta (first day)
  const mockDataPointNoChange: ChartDataPoint = {
    date: new Date('2025-01-01'),
    dateLabel: '01/01',
    amount: 500.00,
    amountLabel: '$500.00',
    delta: null,
    deltaLabel: null,
    deltaColor: null,
  };

  describe('Rendering Behavior', () => {
    test('returns null when not active', () => {
      const { container } = render(
        <CustomTooltip active={false} payload={undefined} />
      );

      expect(container.firstChild).toBeNull();
    });

    test('returns null when payload is undefined', () => {
      const { container } = render(
        <CustomTooltip active={true} payload={undefined} />
      );

      expect(container.firstChild).toBeNull();
    });

    test('returns null when payload is empty array', () => {
      const { container } = render(
        <CustomTooltip active={true} payload={[]} />
      );

      expect(container.firstChild).toBeNull();
    });

    test('renders when active and has valid payload', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should render tooltip content
      expect(screen.getByText('January 15, 2025')).toBeInTheDocument();
      expect(screen.getByText('$1,234.56')).toBeInTheDocument();
    });
  });

  describe('Date Formatting', () => {
    test('displays full formatted date', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should format date as "January 15, 2025"
      expect(screen.getByText('January 15, 2025')).toBeInTheDocument();
    });

    test('formats different months correctly', () => {
      const marchData: ChartDataPoint = {
        ...mockDataPointIncrease,
        date: new Date('2025-03-20'),
      };

      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: marchData,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      expect(screen.getByText('March 20, 2025')).toBeInTheDocument();
    });
  });

  describe('Amount Display', () => {
    test('displays formatted amount', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should display pre-formatted amount
      expect(screen.getByText('$1,234.56')).toBeInTheDocument();
    });

    test('displays large amounts correctly', () => {
      const largeAmount: ChartDataPoint = {
        ...mockDataPointIncrease,
        amount: 123456.78,
        amountLabel: '$123,456.78',
      };

      const mockPayload: TooltipPayload[] = [
        {
          value: 123456.78,
          payload: largeAmount,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      expect(screen.getByText('$123,456.78')).toBeInTheDocument();
    });

    test('displays small amounts correctly', () => {
      const smallAmount: ChartDataPoint = {
        ...mockDataPointIncrease,
        amount: 12.34,
        amountLabel: '$12.34',
      };

      const mockPayload: TooltipPayload[] = [
        {
          value: 12.34,
          payload: smallAmount,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      expect(screen.getByText('$12.34')).toBeInTheDocument();
    });
  });

  describe('Delta Display with Increase (Red)', () => {
    test('displays delta with increase (red color)', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should show delta label
      expect(screen.getByText(/↑ 15.2% vs yesterday/)).toBeInTheDocument();
    });

    test('applies red color class for increase', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(
        <CustomTooltip active={true} payload={mockPayload} />
      );

      // Should have text-destructive class (red)
      const deltaElement = screen.getByText(/↑ 15.2% vs yesterday/);
      expect(deltaElement).toHaveClass('text-destructive');
    });

    test('displays upward arrow for increase', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should show upward arrow (↑)
      expect(screen.getByText(/↑/)).toBeInTheDocument();
    });
  });

  describe('Delta Display with Decrease (Green)', () => {
    test('displays delta with decrease (green color)', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 987.65,
          payload: mockDataPointDecrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should show delta label
      expect(screen.getByText(/↓ 20.0% vs yesterday/)).toBeInTheDocument();
    });

    test('applies green color class for decrease', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 987.65,
          payload: mockDataPointDecrease,
        },
      ];

      render(
        <CustomTooltip active={true} payload={mockPayload} />
      );

      // Should have text-green-600 class
      const deltaElement = screen.getByText(/↓ 20.0% vs yesterday/);
      expect(deltaElement).toHaveClass('text-green-600');
    });

    test('displays downward arrow for decrease', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 987.65,
          payload: mockDataPointDecrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should show downward arrow (↓)
      expect(screen.getByText(/↓/)).toBeInTheDocument();
    });
  });

  describe('Delta Display - No Change', () => {
    test('does not display delta when deltaLabel is null', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 500.00,
          payload: mockDataPointNoChange,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should NOT show delta text
      expect(screen.queryByText(/vs yesterday/)).not.toBeInTheDocument();
    });

    test('displays zero change delta correctly', () => {
      const zeroChangeDelta: ChartDataPoint = {
        ...mockDataPointNoChange,
        delta: 0,
        deltaLabel: '↑ 0.0%',
        deltaColor: 'red',
      };

      const mockPayload: TooltipPayload[] = [
        {
          value: 500.00,
          payload: zeroChangeDelta,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // Should show 0% change
      expect(screen.getByText(/↑ 0.0% vs yesterday/)).toBeInTheDocument();
    });
  });

  describe('Styling and Layout', () => {
    test('has correct container classes', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      const { container } = render(
        <CustomTooltip active={true} payload={mockPayload} />
      );

      const tooltipDiv = container.querySelector('.bg-card');
      expect(tooltipDiv).toBeInTheDocument();
      expect(tooltipDiv).toHaveClass(
        'bg-card',
        'border',
        'border-border',
        'rounded-lg',
        'shadow-lg',
        'p-3',
        'min-w-[200px]'
      );
    });

    test('date has correct text styling', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      const dateElement = screen.getByText('January 15, 2025');
      expect(dateElement).toHaveClass('text-sm', 'font-semibold', 'mb-1', 'text-foreground');
    });

    test('amount has correct text styling', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      const amountElement = screen.getByText('$1,234.56');
      expect(amountElement).toHaveClass('text-2xl', 'font-bold', 'text-foreground');
    });

    test('delta has correct text styling', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      const deltaElement = screen.getByText(/↑ 15.2% vs yesterday/);
      expect(deltaElement).toHaveClass('text-sm', 'mt-1', 'font-medium');
    });
  });

  describe('Edge Cases', () => {
    test('handles very large delta percentages', () => {
      const largeIncrease: ChartDataPoint = {
        ...mockDataPointIncrease,
        delta: 150.5,
        deltaLabel: '↑ 150.5%',
        deltaColor: 'red',
      };

      const mockPayload: TooltipPayload[] = [
        {
          value: 5000.00,
          payload: largeIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      expect(screen.getByText(/↑ 150.5% vs yesterday/)).toBeInTheDocument();
    });

    test('handles very small delta percentages', () => {
      const smallIncrease: ChartDataPoint = {
        ...mockDataPointIncrease,
        delta: 0.1,
        deltaLabel: '↑ 0.1%',
        deltaColor: 'red',
      };

      const mockPayload: TooltipPayload[] = [
        {
          value: 1000.10,
          payload: smallIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      expect(screen.getByText(/↑ 0.1% vs yesterday/)).toBeInTheDocument();
    });

    test('handles malformed payload gracefully', () => {
      const { container } = render(
        <CustomTooltip active={true} payload={[{ value: 123 }] as unknown as TooltipPayload[]} />
      );

      // Should not crash, may return null or render partial content
      // This test validates the component doesn't throw
      expect(container).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('tooltip content is readable', () => {
      const mockPayload: TooltipPayload[] = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      render(<CustomTooltip active={true} payload={mockPayload} />);

      // All text should be visible and readable
      expect(screen.getByText('January 15, 2025')).toBeVisible();
      expect(screen.getByText('$1,234.56')).toBeVisible();
      expect(screen.getByText(/↑ 15.2% vs yesterday/)).toBeVisible();
    });

    test('color contrast for delta text is sufficient', () => {
      // Red text for increase
      const mockPayloadIncrease = [
        {
          value: 1234.56,
          payload: mockDataPointIncrease,
        },
      ];

      const { rerender } = render(
        <CustomTooltip active={true} payload={mockPayloadIncrease} />
      );

      const deltaElementRed = screen.getByText(/↑ 15.2% vs yesterday/);
      expect(deltaElementRed).toHaveClass('text-destructive');

      // Green text for decrease
      const mockPayloadDecrease = [
        {
          value: 987.65,
          payload: mockDataPointDecrease,
        },
      ];

      rerender(<CustomTooltip active={true} payload={mockPayloadDecrease} />);

      const deltaElementGreen = screen.getByText(/↓ 20.0% vs yesterday/);
      expect(deltaElementGreen).toHaveClass('text-green-600');
    });
  });
});
