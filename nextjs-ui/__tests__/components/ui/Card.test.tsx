import { render, screen } from '@testing-library/react'
import { Card } from '@/components/ui/Card'

describe('Card', () => {
  it('renders children correctly', () => {
    render(<Card data-testid="card">Card content</Card>)
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  describe('glassmorphism', () => {
    it('applies glass-card class', () => {
      render(<Card data-testid="card">Glass card</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('glass-card')
    })
  })

  describe('padding variants', () => {
    it('applies medium padding by default', () => {
      render(<Card data-testid="card">Medium padding</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('p-6')
    })

    it('applies no padding when padding="none"', () => {
      render(<Card padding="none" data-testid="card">No padding</Card>)
      const card = screen.getByTestId('card')
      expect(card).not.toHaveClass('p-3')
      expect(card).not.toHaveClass('p-6')
      expect(card).not.toHaveClass('p-8')
    })

    it('applies small padding', () => {
      render(<Card padding="sm" data-testid="card">Small padding</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('p-3')
    })

    it('applies large padding', () => {
      render(<Card padding="lg" data-testid="card">Large padding</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('p-8')
    })
  })

  describe('hover effect', () => {
    it('applies hover transform by default', () => {
      render(<Card data-testid="card">Hover effect</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('hover:scale-[1.02]')
    })

    it('disables hover transform when hover=false', () => {
      render(<Card hover={false} data-testid="card">No hover</Card>)
      const card = screen.getByTestId('card')
      expect(card).not.toHaveClass('hover:scale-[1.02]')
    })
  })

  describe('custom styling', () => {
    it('accepts custom className', () => {
      render(<Card className="custom-class" data-testid="card">Custom</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('custom-class')
    })

    it('passes through HTML div attributes', () => {
      render(<Card data-testid="test-card">Test</Card>)
      expect(screen.getByTestId('test-card')).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('renders as div element', () => {
      render(<Card data-testid="card">Div card</Card>)
      const card = screen.getByTestId('card')
      expect(card.tagName).toBe('DIV')
    })

    it('supports aria attributes', () => {
      render(<Card aria-label="Information card">Info</Card>)
      const card = screen.getByLabelText('Information card')
      expect(card).toBeInTheDocument()
    })
  })

  describe('nested content', () => {
    it('renders complex nested children', () => {
      render(
        <Card>
          <h2>Title</h2>
          <p>Description</p>
          <button>Action</button>
        </Card>
      )

      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Description')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
    })
  })
})
