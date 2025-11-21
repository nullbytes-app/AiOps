/**
 * ThemeProvider Component Tests
 *
 * Tests for the ThemeProvider that manages application theme state.
 */

import React from 'react'
import { render } from '@testing-library/react'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { useThemeStore } from '@/lib/stores/themeStore'

// Mock the theme store
jest.mock('@/lib/stores/themeStore')

type ThemeState = {
  theme: 'light' | 'dark'
  setTheme: jest.Mock
  toggleTheme: jest.Mock
}

type ThemeSelector<T> = (state: ThemeState) => T

describe('ThemeProvider', () => {
  const mockUseThemeStore = useThemeStore as jest.MockedFunction<
    typeof useThemeStore
  >

  beforeEach(() => {
    jest.clearAllMocks()
    // Reset document classes
    document.documentElement.className = ''
  })

  it('renders children', () => {
    // Mock the selector function that's used in ThemeProvider
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'light' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    const { getByText } = render(
      <ThemeProvider>
        <div>Test Child</div>
      </ThemeProvider>
    )

    expect(getByText('Test Child')).toBeInTheDocument()
  })

  it('applies light theme class to document root', () => {
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'light' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('applies dark theme class to document root', () => {
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'dark' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('removes previous theme class when theme changes', () => {
    // Start with light theme
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'light' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    const { rerender } = render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    // Change to dark theme
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'dark' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })
    rerender(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('renders multiple children correctly', () => {
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'light' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    const { getByText } = render(
      <ThemeProvider>
        <div>Child 1</div>
        <div>Child 2</div>
        <div>Child 3</div>
      </ThemeProvider>
    )

    expect(getByText('Child 1')).toBeInTheDocument()
    expect(getByText('Child 2')).toBeInTheDocument()
    expect(getByText('Child 3')).toBeInTheDocument()
  })

  it('renders nested children correctly', () => {
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'light' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    const { getByText } = render(
      <ThemeProvider>
        <div>
          <div>
            <span>Deeply Nested Child</span>
          </div>
        </div>
      </ThemeProvider>
    )

    expect(getByText('Deeply Nested Child')).toBeInTheDocument()
  })

  it('subscribes to theme store on mount', () => {
    mockUseThemeStore.mockImplementation((selector: ThemeSelector<unknown>) => {
      const state = {
        theme: 'light' as const,
        setTheme: jest.fn(),
        toggleTheme: jest.fn(),
      }
      return typeof selector === 'function' ? selector(state) : state
    })

    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    // Verify that useThemeStore was called
    expect(mockUseThemeStore).toHaveBeenCalled()
  })

  it('updates theme class when store theme changes after mount', () => {
    let currentTheme: 'light' | 'dark' = 'light'

    // Mock implementation that returns current theme
    mockUseThemeStore.mockImplementation(
      (selector: ThemeSelector<unknown>) => {
        const state = {
          theme: currentTheme,
          setTheme: jest.fn(),
          toggleTheme: jest.fn(),
        }
        return typeof selector === 'function' ? selector(state) : state
      }
    )

    const { rerender } = render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    expect(document.documentElement.classList.contains('light')).toBe(true)

    // Simulate theme change in store
    currentTheme = 'dark'
    rerender(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    )

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })
})
