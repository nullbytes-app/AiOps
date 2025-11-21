import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/Badge'

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Status</Badge>)
    expect(screen.getByText('Status')).toBeInTheDocument()
  })

  describe('variants', () => {
    it('renders default variant by default', () => {
      render(<Badge>Default</Badge>)
      const badge = screen.getByText('Default')
      expect(badge).toHaveClass('bg-gray-100')
      expect(badge).toHaveClass('text-gray-700')
    })

    it('renders success variant', () => {
      render(<Badge variant="success">Success</Badge>)
      const badge = screen.getByText('Success')
      expect(badge).toHaveClass('bg-accent-green/20')
      expect(badge).toHaveClass('text-accent-green')
    })

    it('renders warning variant', () => {
      render(<Badge variant="warning">Warning</Badge>)
      const badge = screen.getByText('Warning')
      expect(badge).toHaveClass('bg-accent-orange/20')
      expect(badge).toHaveClass('text-accent-orange')
    })

    it('renders error variant', () => {
      render(<Badge variant="error">Error</Badge>)
      const badge = screen.getByText('Error')
      expect(badge).toHaveClass('bg-red-100')
      expect(badge).toHaveClass('text-red-700')
    })

    it('renders info variant', () => {
      render(<Badge variant="info">Info</Badge>)
      const badge = screen.getByText('Info')
      expect(badge).toHaveClass('bg-accent-blue/20')
      expect(badge).toHaveClass('text-accent-blue')
    })
  })

  describe('sizes', () => {
    it('renders medium size by default', () => {
      render(<Badge>Medium</Badge>)
      const badge = screen.getByText('Medium')
      expect(badge).toHaveClass('px-3')
      expect(badge).toHaveClass('py-1')
      expect(badge).toHaveClass('text-sm')
    })

    it('renders small size', () => {
      render(<Badge size="sm">Small</Badge>)
      const badge = screen.getByText('Small')
      expect(badge).toHaveClass('px-2')
      expect(badge).toHaveClass('py-0.5')
      expect(badge).toHaveClass('text-xs')
    })
  })

  describe('styling', () => {
    it('applies base styles', () => {
      render(<Badge>Base</Badge>)
      const badge = screen.getByText('Base')
      expect(badge).toHaveClass('inline-flex')
      expect(badge).toHaveClass('items-center')
      expect(badge).toHaveClass('gap-1')
      expect(badge).toHaveClass('rounded-full')
      expect(badge).toHaveClass('font-medium')
      expect(badge).toHaveClass('whitespace-nowrap')
    })

    it('accepts custom className', () => {
      render(<Badge className="custom-badge">Custom</Badge>)
      expect(screen.getByText('Custom')).toHaveClass('custom-badge')
    })
  })

  describe('HTML attributes', () => {
    it('renders as span element', () => {
      render(<Badge>Span</Badge>)
      const badge = screen.getByText('Span')
      expect(badge.tagName).toBe('SPAN')
    })

    it('passes through HTML span attributes', () => {
      render(<Badge data-testid="test-badge" aria-label="Status badge">Test</Badge>)
      expect(screen.getByTestId('test-badge')).toBeInTheDocument()
      expect(screen.getByLabelText('Status badge')).toBeInTheDocument()
    })
  })

  describe('nested content', () => {
    it('renders icon and text together', () => {
      render(
        <Badge>
          <span>✓</span>
          <span>Active</span>
        </Badge>
      )
      expect(screen.getByText('✓')).toBeInTheDocument()
      expect(screen.getByText('Active')).toBeInTheDocument()
    })
  })

  describe('variant and size combinations', () => {
    it('renders success badge with small size', () => {
      render(<Badge variant="success" size="sm">Success Small</Badge>)
      const badge = screen.getByText('Success Small')
      expect(badge).toHaveClass('bg-accent-green/20')
      expect(badge).toHaveClass('px-2')
      expect(badge).toHaveClass('text-xs')
    })

    it('renders error badge with medium size', () => {
      render(<Badge variant="error" size="md">Error Medium</Badge>)
      const badge = screen.getByText('Error Medium')
      expect(badge).toHaveClass('bg-red-100')
      expect(badge).toHaveClass('px-3')
      expect(badge).toHaveClass('text-sm')
    })
  })
})
