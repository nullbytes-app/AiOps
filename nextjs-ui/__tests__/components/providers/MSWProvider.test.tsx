/**
 * MSWProvider Component Tests
 *
 * Tests for the MSWProvider component that conditionally initializes
 * Mock Service Worker in development mode.
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MSWProvider } from '@/components/providers/MSWProvider'

// Mock the MSW browser module
const mockStartMSW = jest.fn()
jest.mock('@/mocks/browser', () => ({
  startMSW: mockStartMSW,
}))

describe('MSWProvider', () => {
  const originalNodeEnv = process.env.NODE_ENV

  beforeEach(() => {
    jest.clearAllMocks()
    mockStartMSW.mockResolvedValue(undefined)
  })

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv
  })

  it('renders children immediately in production mode', () => {
    process.env.NODE_ENV = 'production'

    render(
      <MSWProvider>
        <div>Test Child</div>
      </MSWProvider>
    )

    expect(screen.getByText('Test Child')).toBeInTheDocument()
    expect(mockStartMSW).not.toHaveBeenCalled()
  })

  it('shows loading state while initializing MSW in development', () => {
    process.env.NODE_ENV = 'development'

    // Make startMSW hang to keep loading state
    mockStartMSW.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    )

    render(
      <MSWProvider>
        <div>Test Child</div>
      </MSWProvider>
    )

    // Should show loading spinner
    expect(
      screen.getByText('Initializing development environment...')
    ).toBeInTheDocument()

    // Should not render children yet
    expect(screen.queryByText('Test Child')).not.toBeInTheDocument()
  })

  it('renders children after MSW initialization in development', async () => {
    process.env.NODE_ENV = 'development'

    render(
      <MSWProvider>
        <div>Test Child</div>
      </MSWProvider>
    )

    // Wait for MSW to initialize
    await waitFor(() => {
      expect(mockStartMSW).toHaveBeenCalledTimes(1)
    })

    // Should render children after initialization
    await waitFor(() => {
      expect(screen.getByText('Test Child')).toBeInTheDocument()
    })

    // Should not show loading state anymore
    expect(
      screen.queryByText('Initializing development environment...')
    ).not.toBeInTheDocument()
  })

  it('renders children even if MSW initialization fails', async () => {
    process.env.NODE_ENV = 'development'

    // Simulate MSW initialization failure
    const consoleErrorSpy = jest
      .spyOn(console, 'error')
      .mockImplementation(() => {})
    mockStartMSW.mockRejectedValue(new Error('MSW init failed'))

    render(
      <MSWProvider>
        <div>Test Child</div>
      </MSWProvider>
    )

    // Should still render children despite error
    await waitFor(() => {
      expect(screen.getByText('Test Child')).toBeInTheDocument()
    })

    // Should log error
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      '[MSW] Failed to initialize:',
      expect.any(Error)
    )

    consoleErrorSpy.mockRestore()
  })

  it('has proper loading UI styling', () => {
    process.env.NODE_ENV = 'development'

    mockStartMSW.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    )

    const { container } = render(
      <MSWProvider>
        <div>Test Child</div>
      </MSWProvider>
    )

    // Check for loading spinner classes
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('border-accent-blue/20')
    expect(spinner).toHaveClass('border-t-accent-blue')

    // Check for centered layout
    const centerContainer = container.querySelector('.min-h-screen')
    expect(centerContainer).toHaveClass('flex')
    expect(centerContainer).toHaveClass('items-center')
    expect(centerContainer).toHaveClass('justify-center')
  })

  it('only initializes MSW once', async () => {
    process.env.NODE_ENV = 'development'

    const { rerender } = render(
      <MSWProvider>
        <div>Test Child 1</div>
      </MSWProvider>
    )

    await waitFor(() => {
      expect(mockStartMSW).toHaveBeenCalledTimes(1)
    })

    // Re-render with different children
    rerender(
      <MSWProvider>
        <div>Test Child 2</div>
      </MSWProvider>
    )

    // Should not call startMSW again
    expect(mockStartMSW).toHaveBeenCalledTimes(1)
  })

  it('passes through all children props correctly', async () => {
    process.env.NODE_ENV = 'development'

    render(
      <MSWProvider>
        <div data-testid="child-1">Child 1</div>
        <div data-testid="child-2">Child 2</div>
        <div data-testid="child-3">
          <span>Nested Child</span>
        </div>
      </MSWProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('child-1')).toBeInTheDocument()
    })

    expect(screen.getByTestId('child-2')).toBeInTheDocument()
    expect(screen.getByTestId('child-3')).toBeInTheDocument()
    expect(screen.getByText('Nested Child')).toBeInTheDocument()
  })
})
