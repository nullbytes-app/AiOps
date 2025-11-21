import { render, screen } from '@testing-library/react'
import { Loading } from '@/components/ui/Loading'

describe('Loading', () => {
  describe('spinner rendering', () => {
    it('renders loading spinner', () => {
      const { container } = render(<Loading />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
      expect(spinner).toHaveClass('border-4')
      expect(spinner).toHaveClass('border-accent-blue/20')
      expect(spinner).toHaveClass('border-t-accent-blue')
      expect(spinner).toHaveClass('rounded-full')
    })

    it('renders without text by default', () => {
      render(<Loading />)
      const text = screen.queryByText(/./i)
      expect(text).not.toBeInTheDocument()
    })
  })

  describe('sizes', () => {
    it('renders medium size by default', () => {
      const { container } = render(<Loading />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toHaveClass('w-8')
      expect(spinner).toHaveClass('h-8')
    })

    it('renders small size', () => {
      const { container } = render(<Loading size="sm" />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toHaveClass('w-4')
      expect(spinner).toHaveClass('h-4')
    })

    it('renders large size', () => {
      const { container } = render(<Loading size="lg" />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toHaveClass('w-12')
      expect(spinner).toHaveClass('h-12')
    })
  })

  describe('loading text', () => {
    it('renders text when provided', () => {
      render(<Loading text="Loading..." />)
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('applies correct styles to text', () => {
      render(<Loading text="Please wait" />)
      const text = screen.getByText('Please wait')
      expect(text).toHaveClass('text-sm')
      expect(text).toHaveClass('text-text-secondary')
      expect(text).toHaveClass('animate-pulse')
    })

    it('renders custom loading messages', () => {
      render(<Loading text="Fetching data..." />)
      expect(screen.getByText('Fetching data...')).toBeInTheDocument()
    })
  })

  describe('layout', () => {
    it('applies flex container styles', () => {
      const { container } = render(<Loading />)
      const wrapper = container.firstChild as HTMLElement
      expect(wrapper).toHaveClass('flex')
      expect(wrapper).toHaveClass('flex-col')
      expect(wrapper).toHaveClass('items-center')
      expect(wrapper).toHaveClass('justify-center')
      expect(wrapper).toHaveClass('gap-3')
    })

    it('accepts custom className', () => {
      const { container } = render(<Loading className="custom-loading" />)
      const wrapper = container.firstChild as HTMLElement
      expect(wrapper).toHaveClass('custom-loading')
    })
  })

  describe('HTML attributes', () => {
    it('renders as div element', () => {
      const { container } = render(<Loading />)
      expect(container.firstChild?.nodeName).toBe('DIV')
    })

    it('passes through HTML div attributes', () => {
      const { container } = render(<Loading data-testid="test-loading" aria-label="Loading content" />)
      expect(container.querySelector('[data-testid="test-loading"]')).toBeInTheDocument()
      expect(container.querySelector('[aria-label="Loading content"]')).toBeInTheDocument()
    })
  })

  describe('size and text combinations', () => {
    it('renders small spinner with text', () => {
      const { container } = render(<Loading size="sm" text="Loading..." />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toHaveClass('w-4')
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('renders large spinner with text', () => {
      const { container } = render(<Loading size="lg" text="Please wait..." />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toHaveClass('w-12')
      expect(screen.getByText('Please wait...')).toBeInTheDocument()
    })
  })

  describe('animations', () => {
    it('applies spin animation to spinner', () => {
      const { container } = render(<Loading />)
      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('applies pulse animation to text', () => {
      render(<Loading text="Loading..." />)
      const text = screen.getByText('Loading...')
      expect(text).toHaveClass('animate-pulse')
    })
  })
})
