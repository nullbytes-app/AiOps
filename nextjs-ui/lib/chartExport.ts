/**
 * Chart Export Utilities
 *
 * Client-side chart export using html2canvas.
 * Follows 2025 best practices for high-resolution PNG generation.
 *
 * Maps to Story: nextjs-story-10-llm-cost-dashboard-trend-chart (AC#4)
 *
 * Research Notes:
 * - html2canvas v1.4.1+ with scale: 2 for Retina displays
 * - Fixed dimensions (1920x600px) for consistency
 * - useCORS for external images (design system icons)
 */

import html2canvas from 'html2canvas';
import { format } from 'date-fns';

/**
 * Export chart as high-resolution PNG image
 *
 * Captures the chart DOM element and downloads it as a PNG file.
 * Uses 2x scale for high-resolution displays (Retina).
 *
 * Features:
 * - 1920x600px output (consistent dimensions)
 * - 2x scale for high quality
 * - Filename includes current date
 * - Handles CORS for external images
 *
 * @param chartRef - React ref to chart container div
 * @throws Error if chart ref is not available or canvas generation fails
 *
 * @example
 * ```tsx
 * const chartRef = useRef<HTMLDivElement>(null);
 *
 * <div ref={chartRef}>
 *   <DailySpendChart data={data} />
 * </div>
 *
 * <Button onClick={() => exportChartAsPNG(chartRef)}>
 *   Export as PNG
 * </Button>
 * ```
 */
export async function exportChartAsPNG(
  chartRef: React.RefObject<HTMLDivElement>
): Promise<void> {
  if (!chartRef.current) {
    throw new Error('Chart ref is not available');
  }

  try {
    // Generate canvas from DOM element
    const canvas = await html2canvas(chartRef.current, {
      backgroundColor: '#ffffff', // White background (matches design system card)
      scale: 2, // 2x resolution for high-quality export (Retina displays)
      width: 1920, // Fixed width for consistency
      height: 600, // Fixed height for consistency
      useCORS: true, // Enable CORS for external images (design system icons)
      logging: false, // Disable console logs
      onclone: (clonedDoc) => {
        // Optional: Adjust cloned document for export (e.g., hide buttons)
        const clonedElement = clonedDoc.querySelector('[data-export-hide]');
        if (clonedElement) {
          (clonedElement as HTMLElement).style.display = 'none';
        }
      },
    });

    // Convert canvas to PNG data URL
    const dataUrl = canvas.toDataURL('image/png');

    // Create download link and trigger download
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = `llm-costs-trend-${format(new Date(), 'yyyy-MM-dd')}.png`;
    document.body.appendChild(link); // Required for Firefox
    link.click();
    document.body.removeChild(link); // Clean up
  } catch (error) {
    console.error('Failed to export chart:', error);
    throw new Error(
      `Chart export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}
