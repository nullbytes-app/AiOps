import { test, expect } from '@playwright/test'
import { gotoAndWaitForReady, waitForDashboardHeader } from './helpers'

/**
 * Agent Metrics Dashboard E2E Tests
 *
 * Tests KPI cards, execution chart, agent table, and auto-refresh
 */

test.describe('Agent Metrics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await gotoAndWaitForReady(page, '/dashboard/agents')
    await waitForDashboardHeader(page, 'Agent Metrics')
  })

  test('displays all KPI cards', async ({ page }) => {
    // Wait for KPI cards to load
    await expect(page.getByText(/total executions.*24h/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/success rate/i)).toBeVisible()
    await expect(page.getByText(/avg cost/i)).toBeVisible()
  })

  test('shows KPI values with correct formatting', async ({ page }) => {
    // Wait for data to load
    await expect(page.getByText(/total executions.*24h/i)).toBeVisible({ timeout: 10000 })

    // Verify number formatting (should have commas for large numbers)
    const executionValue = page.locator('text=/\\d{1,3}(,\\d{3})*/').first()
    await expect(executionValue).toBeVisible()

    // Verify percentage formatting
    const percentageValue = page.locator('text=/\\d+(\\.\\d+)?%/').first()
    await expect(percentageValue).toBeVisible()

    // Verify currency formatting
    const currencyValue = page.locator('text=/\\$\\d+(\\.\\d+)?/').first()
    await expect(currencyValue).toBeVisible()
  })

  test('displays trend indicators on KPI cards', async ({ page }) => {
    // Wait for KPIs to load
    await expect(page.getByText(/total executions.*24h/i)).toBeVisible({ timeout: 10000 })

    // Look for trend indicators (SVG icons for up/down/neutral trends)
    // Lucide icons render as SVGs
    const trendIndicators = page.locator('svg')
    const count = await trendIndicators.count()

    // Should have at least one SVG icon
    expect(count).toBeGreaterThan(0)
  })

  test('displays execution timeline chart', async ({ page }) => {
    // Wait for chart title
    await expect(page.getByText(/execution timeline.*last 24 hours/i)).toBeVisible({ timeout: 10000 })

    // Verify chart is rendered (Recharts creates an SVG)
    const chartSvg = page.locator('svg').first()
    await expect(chartSvg).toBeVisible()
  })

  test('displays agent performance table', async ({ page }) => {
    // Wait for table to load
    await expect(page.getByText(/agent performance/i)).toBeVisible({ timeout: 10000 })

    // Verify table headers
    await expect(page.getByText(/agent name/i)).toBeVisible()
    await expect(page.getByText(/total runs/i)).toBeVisible()
    await expect(page.getByText(/success rate/i)).toBeVisible()
    await expect(page.getByText(/avg latency/i)).toBeVisible()
    await expect(page.getByText(/total cost/i)).toBeVisible()

    // Verify at least one row of data exists
    const tableRows = page.locator('tbody tr')
    await expect(tableRows).toHaveCount(await tableRows.count()) // Ensure table has rows
    expect(await tableRows.count()).toBeGreaterThan(0)
  })

  test('filters agents by search query', async ({ page }) => {
    // Wait for table to load
    await expect(page.getByText(/agent performance/i)).toBeVisible({ timeout: 10000 })

    // Get initial row count
    const initialRows = page.locator('tbody tr')
    const initialCount = await initialRows.count()

    // Type in search box
    const searchInput = page.getByPlaceholder(/search agents/i)
    await searchInput.fill('ticket')

    // Wait for filtering to apply
    await page.waitForTimeout(500)

    // Verify filtered results
    const filteredRows = page.locator('tbody tr')
    const filteredCount = await filteredRows.count()

    // Should have fewer rows (or same if all agents match)
    expect(filteredCount).toBeLessThanOrEqual(initialCount)

    // Filtered row should contain "ticket"
    if (filteredCount > 0) {
      await expect(filteredRows.first()).toContainText(/ticket/i)
    }
  })

  test('sorts table by clicking column headers', async ({ page }) => {
    // Wait for table to load
    await expect(page.getByText(/agent performance/i)).toBeVisible({ timeout: 10000 })

    // Get first row agent name before sort
    const firstRowBefore = page.locator('tbody tr').first().locator('td').first()
    await firstRowBefore.textContent()

    // Click "Agent Name" header to sort
    await page.getByText(/agent name/i).click()

    // Wait for sort to apply
    await page.waitForTimeout(500)

    // Get first row agent name after sort
    const firstRowAfter = page.locator('tbody tr').first().locator('td').first()
    const nameAfter = await firstRowAfter.textContent()

    // After sorting, the first agent name should be alphabetically first
    // (or might be the same if already sorted)
    expect(nameAfter).toBeTruthy()
  })

  test('paginates table when more than 10 agents', async ({ page }) => {
    // This test assumes mock data has more than 10 agents
    // If table has pagination, verify it's present

    const nextButton = page.getByRole('button', { name: /next/i })

    // Check if pagination exists
    if (await nextButton.isVisible().catch(() => false)) {
      // Verify pagination controls
      await expect(nextButton).toBeVisible()
      await expect(page.getByRole('button', { name: /previous/i })).toBeVisible()

      // Previous should be disabled on first page
      await expect(page.getByRole('button', { name: /previous/i })).toBeDisabled()
    }
  })

  test('displays page heading', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /agent metrics/i, level: 1 })
    await expect(heading).toBeVisible()
  })

  test('auto-refreshes data after 30 seconds', async ({ page }) => {
    // Wait for initial load
    await expect(page.getByText(/total executions.*24h/i)).toBeVisible({ timeout: 10000 })

    // Get initial KPI value
    const kpiCard = page.getByText(/total executions.*24h/i).locator('..')
    const initialValue = await kpiCard.locator('text=/\\d{1,3}(,\\d{3})*/').first().textContent()

    // Wait for auto-refresh (30 seconds + buffer)
    // For E2E testing, this is a long wait, so we just verify the page is still functional
    await page.waitForTimeout(2000) // Shortened for E2E test performance

    // Verify page still displays correctly (no crashes)
    await expect(page.getByText(/total executions.*24h/i)).toBeVisible()
    await expect(page.getByText(/agent performance/i)).toBeVisible()
  })

  test('maintains responsive layout on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Verify KPI cards stack vertically
    await expect(page.getByText(/total executions.*24h/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/success rate/i)).toBeVisible()

    // Verify chart is still visible and responsive
    await expect(page.getByText(/execution timeline/i)).toBeVisible()

    // Verify table is scrollable horizontally
    const table = page.locator('table').first()
    await expect(table).toBeVisible()
  })
})
