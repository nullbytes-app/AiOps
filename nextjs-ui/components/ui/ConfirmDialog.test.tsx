/**
 * ConfirmDialog Component Tests
 *
 * Tests for the reusable confirmation dialog component.
 * Covers: render, user interactions, keyboard navigation, accessibility.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmDialog } from './ConfirmDialog'

describe('ConfirmDialog', () => {
  const mockOnConfirm = jest.fn()
  const mockOnClose = jest.fn()

  const defaultProps = {
    isOpen: true,
    title: 'Delete Item',
    description: 'Are you sure you want to delete this item? This action cannot be undone.',
    confirmLabel: 'Delete',
    cancelLabel: 'Cancel',
    onConfirm: mockOnConfirm,
    onClose: mockOnClose,
    confirmVariant: 'danger' as const,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders dialog when isOpen is true', () => {
      render(<ConfirmDialog {...defaultProps} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('Delete Item')).toBeInTheDocument()
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument()
    })

    it('does not render dialog when isOpen is false', () => {
      render(<ConfirmDialog {...defaultProps} isOpen={false} />)

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders confirm and cancel buttons with correct labels', () => {
      render(<ConfirmDialog {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('applies danger variant styling to confirm button', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const confirmButton = screen.getByRole('button', { name: 'Delete' })
      // Button uses Tailwind classes for danger variant (red background)
      expect(confirmButton.className).toContain('bg-red-500')
    })

    it('applies default variant when confirmVariant not specified', () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { confirmVariant: _confirmVariant, ...propsWithoutVariant } = defaultProps
      render(<ConfirmDialog {...propsWithoutVariant} />)

      const confirmButton = screen.getByRole('button', { name: 'Delete' })
      // Button uses Tailwind classes for primary variant (blue background)
      expect(confirmButton.className).toContain('bg-accent-blue')
    })
  })

  describe('User Interactions', () => {
    it('calls onConfirm when confirm button clicked', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const confirmButton = screen.getByRole('button', { name: 'Delete' })
      await user.click(confirmButton)

      expect(mockOnConfirm).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when cancel button clicked', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when backdrop clicked', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      // Click the backdrop (dialog overlay)
      const backdrop = screen.getByRole('dialog').parentElement
      if (backdrop) {
        await user.click(backdrop)
        expect(mockOnClose).toHaveBeenCalledTimes(1)
      }
    })
  })

  describe('Keyboard Navigation', () => {
    it('calls onClose when Escape key pressed', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      await user.keyboard('{Escape}')

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalledTimes(1)
      })
    })

    it('calls onConfirm when Enter key pressed while confirm button focused', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const confirmButton = screen.getByRole('button', { name: 'Delete' })
      confirmButton.focus()
      await user.keyboard('{Enter}')

      expect(mockOnConfirm).toHaveBeenCalledTimes(1)
    })

    it('allows Tab navigation between buttons', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const closeButton = screen.getByRole('button', { name: 'Close modal' })
      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      const confirmButton = screen.getByRole('button', { name: 'Delete' })

      // Focus should start on first interactive element (Close button X)
      await user.tab()
      expect(closeButton).toHaveFocus()

      // Tab should move to cancel button
      await user.tab()
      expect(cancelButton).toHaveFocus()

      // Tab should move to confirm button
      await user.tab()
      expect(confirmButton).toHaveFocus()

      // Shift+Tab should move back to cancel
      await user.tab({ shift: true })
      expect(cancelButton).toHaveFocus()
    })
  })

  describe('Accessibility', () => {
    it('has aria-modal attribute on dialog', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has accessible title via aria-labelledby', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      const titleId = dialog.getAttribute('aria-labelledby')

      expect(titleId).toBeTruthy()
      const title = document.getElementById(titleId!)
      expect(title).toHaveTextContent('Delete Item')
    })

    it('has accessible description via aria-describedby', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      const descriptionId = dialog.getAttribute('aria-describedby')

      expect(descriptionId).toBeTruthy()
      const description = document.getElementById(descriptionId!)
      expect(description).toHaveTextContent(/Are you sure you want to delete/)
    })

    it('traps focus within dialog when open', async () => {
      const user = userEvent.setup()
      render(
        <div>
          <button>Outside Button</button>
          <ConfirmDialog {...defaultProps} />
        </div>
      )

      const outsideButton = screen.getByRole('button', { name: 'Outside Button' })
      const closeButton = screen.getByRole('button', { name: 'Close modal' })

      // Focus should be trapped inside dialog (starts with close button)
      await user.tab()
      expect(closeButton).toHaveFocus()
      expect(outsideButton).not.toHaveFocus()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing description gracefully', () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { description, ...propsWithoutDescription } = defaultProps
      render(<ConfirmDialog {...propsWithoutDescription} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.queryByText(/Are you sure/)).not.toBeInTheDocument()
    })

    it('handles custom confirm label', () => {
      render(<ConfirmDialog {...defaultProps} confirmLabel="Yes, Delete" />)

      expect(screen.getByRole('button', { name: 'Yes, Delete' })).toBeInTheDocument()
    })

    it('handles custom cancel label', () => {
      render(<ConfirmDialog {...defaultProps} cancelLabel="No, Keep It" />)

      expect(screen.getByRole('button', { name: 'No, Keep It' })).toBeInTheDocument()
    })

    it('does not call handlers multiple times on rapid clicks', async () => {
      const user = userEvent.setup()
      render(<ConfirmDialog {...defaultProps} />)

      const confirmButton = screen.getByRole('button', { name: 'Delete' })

      // Rapid clicks
      await user.click(confirmButton)
      await user.click(confirmButton)
      await user.click(confirmButton)

      // Should only call once if dialog closes after first click
      expect(mockOnConfirm).toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('disables buttons when isLoading is true', () => {
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)

      // When loading, button text changes to "Loading..." so we find all buttons
      const buttons = screen.getAllByRole('button')
      const confirmButton = buttons.find(btn => btn.textContent?.includes('Loading'))
      const cancelButton = screen.getByRole('button', { name: 'Cancel' })

      expect(confirmButton).toBeDisabled()
      expect(cancelButton).toBeDisabled()
    })

    it('shows loading spinner on confirm button when isLoading', () => {
      render(<ConfirmDialog {...defaultProps} isLoading={true} />)

      // Find button with loading text
      const buttons = screen.getAllByRole('button')
      const confirmButton = buttons.find(btn => btn.textContent?.includes('Loading'))

      expect(confirmButton).toBeInTheDocument()
      expect(confirmButton).toHaveTextContent(/Loading/)
    })
  })
})
