/**
 * ThemeToggle Component Tests
 *
 * Tests for the theme toggle button that switches between light and dark modes.
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useThemeStore } from '@/lib/stores/themeStore'

// Mock the theme store
jest.mock('@/lib/stores/themeStore')

describe('ThemeToggle', () => {
  const mockToggleTheme = jest.fn()
  const mockUseThemeStore = useThemeStore as jest.MockedFunction<
    typeof useThemeStore
  >

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders theme toggle button', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    render(<ThemeToggle />)

    const button = screen.getByRole('button', {
      name: /switch to dark mode/i,
    })
    expect(button).toBeInTheDocument()
  })

  it('shows moon icon in light mode', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    const { container } = render(<ThemeToggle />)

    // Moon icon should be visible (lucide-react uses SVG with specific class)
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Switch to dark mode')

    // Check that container has the button with moon icon
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('shows sun icon in dark mode', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'dark',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    const { container } = render(<ThemeToggle />)

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Switch to light mode')

    // Check that container has the button with sun icon
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('calls toggleTheme when clicked', async () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    const user = userEvent.setup()
    render(<ThemeToggle />)

    const button = screen.getByRole('button')
    await user.click(button)

    expect(mockToggleTheme).toHaveBeenCalledTimes(1)
  })

  it('calls toggleTheme multiple times on multiple clicks', async () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    const user = userEvent.setup()
    render(<ThemeToggle />)

    const button = screen.getByRole('button')

    await user.click(button)
    await user.click(button)
    await user.click(button)

    expect(mockToggleTheme).toHaveBeenCalledTimes(3)
  })

  it('has glassmorphic styling', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    render(<ThemeToggle />)

    const button = screen.getByRole('button')
    expect(button).toHaveClass('glass-card')
    expect(button).toHaveClass('rounded-lg')
  })

  it('has proper focus styles for accessibility', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    render(<ThemeToggle />)

    const button = screen.getByRole('button')
    expect(button).toHaveClass('focus:outline-none')
    expect(button).toHaveClass('focus:ring-2')
    expect(button).toHaveClass('focus:ring-accent-blue/50')
  })

  it('has hover transition styles', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    render(<ThemeToggle />)

    const button = screen.getByRole('button')
    expect(button).toHaveClass('transition-all')
    expect(button).toHaveClass('duration-200')
    expect(button).toHaveClass('hover:bg-white/50')
  })

  it('updates aria-label when theme changes', () => {
    const { rerender } = render(<ThemeToggle />)

    // Start with light theme
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })
    rerender(<ThemeToggle />)

    let button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Switch to dark mode')

    // Change to dark theme
    mockUseThemeStore.mockReturnValue({
      theme: 'dark',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })
    rerender(<ThemeToggle />)

    button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Switch to light mode')
  })

  it('hides icon from screen readers with aria-hidden', () => {
    mockUseThemeStore.mockReturnValue({
      theme: 'light',
      setTheme: jest.fn(),
      toggleTheme: mockToggleTheme,
    })

    const { container } = render(<ThemeToggle />)

    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-hidden', 'true')
  })
})
