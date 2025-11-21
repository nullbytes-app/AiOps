import { render, screen } from '@testing-library/react'
import { Footer } from '@/components/dashboard/Footer'

describe('Footer', () => {
  describe('rendering', () => {
    it('renders footer element', () => {
      render(<Footer />)
      const footer = screen.getByRole('contentinfo')
      expect(footer).toBeInTheDocument()
    })

    it('applies glassmorphism styles', () => {
      render(<Footer />)
      const footer = screen.getByRole('contentinfo')
      expect(footer).toHaveClass('glass-card')
    })

    it('has correct spacing', () => {
      render(<Footer />)
      const footer = screen.getByRole('contentinfo')
      expect(footer).toHaveClass('mt-6')
      expect(footer).toHaveClass('px-6')
      expect(footer).toHaveClass('py-4')
    })
  })

  describe('copyright', () => {
    it('displays copyright text', () => {
      render(<Footer />)
      expect(screen.getByText(/AI Agents Platform/i)).toBeInTheDocument()
      expect(screen.getByText(/All rights reserved/i)).toBeInTheDocument()
    })

    it('displays current year', () => {
      render(<Footer />)
      const currentYear = new Date().getFullYear()
      expect(screen.getByText(new RegExp(`© ${currentYear}`))).toBeInTheDocument()
    })
  })

  describe('version', () => {
    it('displays version number', () => {
      render(<Footer />)
      expect(screen.getByText('v1.0.0')).toBeInTheDocument()
    })
  })

  describe('quick links', () => {
    it('renders Documentation link', () => {
      render(<Footer />)
      const docLink = screen.getByRole('link', { name: /documentation/i })
      expect(docLink).toBeInTheDocument()
      expect(docLink).toHaveAttribute('href', '/docs')
    })

    it('renders Support link', () => {
      render(<Footer />)
      const supportLink = screen.getByRole('link', { name: /support/i })
      expect(supportLink).toBeInTheDocument()
      expect(supportLink).toHaveAttribute('href', '/support')
    })

    it('applies hover effects to links', () => {
      render(<Footer />)
      const docLink = screen.getByRole('link', { name: /documentation/i })
      expect(docLink).toHaveClass('hover:text-accent-blue')
      expect(docLink).toHaveClass('transition-colors')
      expect(docLink).toHaveClass('duration-fast')
    })
  })

  describe('layout', () => {
    it('uses flexbox layout', () => {
      const { container } = render(<Footer />)
      const innerDiv = container.querySelector('.flex.items-center.justify-between')
      expect(innerDiv).toBeInTheDocument()
    })

    it('applies correct text sizing', () => {
      const { container } = render(<Footer />)
      const innerDiv = container.querySelector('.text-sm')
      expect(innerDiv).toBeInTheDocument()
    })

    it('applies correct text color', () => {
      const { container } = render(<Footer />)
      const innerDiv = container.querySelector('.text-text-secondary')
      expect(innerDiv).toBeInTheDocument()
    })

    it('has proper spacing between right-side items', () => {
      const { container } = render(<Footer />)
      const rightSection = container.querySelector('.gap-6')
      expect(rightSection).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('uses semantic footer element', () => {
      render(<Footer />)
      expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    })

    it('all links are keyboard accessible', () => {
      render(<Footer />)
      const links = screen.getAllByRole('link')
      expect(links.length).toBe(2) // Documentation and Support
      links.forEach(link => {
        expect(link).toHaveAttribute('href')
      })
    })
  })

  describe('responsive behavior', () => {
    it('maintains flex layout for responsiveness', () => {
      const { container } = render(<Footer />)
      const innerDiv = container.querySelector('.flex')
      expect(innerDiv).toHaveClass('items-center')
      expect(innerDiv).toHaveClass('justify-between')
    })
  })
})
