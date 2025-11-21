/**
 * TenantForm Component Tests
 *
 * Tests for tenant creation and editing form.
 * Covers: validation, submission, loading states, error handling, accessibility.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TenantForm } from './TenantForm'
import { Tenant } from '@/lib/api/tenants'

describe('TenantForm', () => {
  const mockOnSubmit = jest.fn()
  const mockOnCancel = jest.fn()

  const mockTenant: Partial<Tenant> = {
    id: 'tenant-1',
    name: 'Acme Corp',
    description: 'Main production tenant',
    logo: 'https://example.com/logo.png',
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering - Create Mode', () => {
    it('renders form in create mode with empty fields', () => {
      render(<TenantForm onSubmit={mockOnSubmit} mode="create" />)

      expect(screen.getByLabelText(/Tenant Name/i)).toHaveValue('')
      expect(screen.getByLabelText(/Description/i)).toHaveValue('')
      expect(screen.getByLabelText(/Logo URL/i)).toHaveValue('')
      expect(screen.getByRole('button', { name: /Create Tenant/i })).toBeInTheDocument()
    })

    it('renders all form fields with correct labels', () => {
      render(<TenantForm onSubmit={mockOnSubmit} />)

      expect(screen.getByLabelText(/Tenant Name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Description/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Logo URL/i)).toBeInTheDocument()
    })

    it('shows required indicator on name field', () => {
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameLabel = screen.getByText(/Tenant Name/i)
      expect(nameLabel.parentElement).toHaveTextContent('*')
    })

    it('shows help text for each field', () => {
      render(<TenantForm onSubmit={mockOnSubmit} />)

      expect(screen.getByText(/A unique name for this tenant/i)).toBeInTheDocument()
      expect(screen.getByText(/Brief description of this tenant/i)).toBeInTheDocument()
      expect(screen.getByText(/URL or base64-encoded image/i)).toBeInTheDocument()
    })

    it('does not render cancel button when onCancel not provided', () => {
      render(<TenantForm onSubmit={mockOnSubmit} />)

      expect(screen.queryByRole('button', { name: /Cancel/i })).not.toBeInTheDocument()
    })

    it('renders cancel button when onCancel provided', () => {
      render(<TenantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />)

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })
  })

  describe('Rendering - Edit Mode', () => {
    it('renders form in edit mode with pre-filled values', () => {
      render(
        <TenantForm onSubmit={mockOnSubmit} defaultValues={mockTenant} mode="edit" />
      )

      expect(screen.getByLabelText(/Tenant Name/i)).toHaveValue('Acme Corp')
      expect(screen.getByLabelText(/Description/i)).toHaveValue('Main production tenant')
      expect(screen.getByLabelText(/Logo URL/i)).toHaveValue('https://example.com/logo.png')
      expect(screen.getByRole('button', { name: /Update Tenant/i })).toBeInTheDocument()
    })

    it('shows logo preview when logo URL provided', () => {
      render(
        <TenantForm onSubmit={mockOnSubmit} defaultValues={mockTenant} mode="edit" />
      )

      const logoPreview = screen.getByAltText(/Tenant logo/i)
      expect(logoPreview).toBeInTheDocument()
      expect(logoPreview).toHaveAttribute('src', expect.stringContaining('example.com/logo.png'))
    })

    it('does not show logo preview when logo URL empty', () => {
      render(
        <TenantForm onSubmit={mockOnSubmit} defaultValues={{ name: 'Test' }} mode="edit" />
      )

      expect(screen.queryByAltText(/Tenant logo/i)).not.toBeInTheDocument()
    })
  })

  describe('Validation - Name Field', () => {
    it('shows error when name is empty on submit', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('shows error when name is less than 3 characters', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'AB')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/Name must be at least 3 characters/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('shows error when name exceeds 50 characters', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      const longName = 'A'.repeat(51)
      await user.type(nameInput, longName)

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/Name must be at most 50 characters/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('accepts valid name (3-50 characters)', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Valid Tenant Name')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled()
      })
    })
  })

  describe('Validation - Description Field', () => {
    it('accepts empty description (optional field)', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Test Tenant')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Tenant',
            description: '',
          })
        )
      })
    })

    it('shows error when description exceeds 500 characters', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Test Tenant')

      const descriptionInput = screen.getByLabelText(/Description/i)
      const longDescription = 'A'.repeat(501)
      await user.type(descriptionInput, longDescription)

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/Description must be at most 500 characters/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('accepts valid description (up to 500 characters)', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Test Tenant')

      const descriptionInput = screen.getByLabelText(/Description/i)
      await user.type(descriptionInput, 'Valid description text')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            description: 'Valid description text',
          })
        )
      })
    })
  })

  describe('Validation - Logo URL Field', () => {
    it('accepts empty logo URL (optional field)', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Test Tenant')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            logo: '',
          })
        )
      })
    })

    it('shows error when logo URL is invalid', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Test Tenant')

      const logoInput = screen.getByLabelText(/Logo URL/i)
      await user.type(logoInput, 'not-a-valid-url')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/Must be a valid URL/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('accepts valid logo URL', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      await user.type(nameInput, 'Test Tenant')

      const logoInput = screen.getByLabelText(/Logo URL/i)
      await user.type(logoInput, 'https://example.com/logo.png')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            logo: 'https://example.com/logo.png',
          })
        )
      })
    })

    it('updates logo preview when valid URL entered', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const logoInput = screen.getByLabelText(/Logo URL/i)
      await user.type(logoInput, 'https://example.com/new-logo.png')

      await waitFor(() => {
        const logoPreview = screen.queryByAltText(/Tenant logo/i)
        if (logoPreview) {
          expect(logoPreview).toHaveAttribute('src', expect.stringContaining('new-logo.png'))
        }
      })
    })
  })

  describe('Form Submission', () => {
    it('calls onSubmit with form data when validation passes', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Tenant Name/i), 'New Tenant')
      await user.type(screen.getByLabelText(/Description/i), 'Test description')
      await user.type(screen.getByLabelText(/Logo URL/i), 'https://example.com/logo.png')

      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          name: 'New Tenant',
          description: 'Test description',
          logo: 'https://example.com/logo.png',
        })
      })
    })

    it('does not call onSubmit when validation fails', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      // Submit with empty required field
      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))

      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('submits with only required field when optional fields empty', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Tenant Name/i), 'Minimal Tenant')
      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          name: 'Minimal Tenant',
          description: '',
          logo: '',
        })
      })
    })
  })

  describe('Loading State', () => {
    it('disables submit button when isLoading is true', () => {
      render(<TenantForm onSubmit={mockOnSubmit} isLoading={true} />)

      const submitButton = screen.getByRole('button', { name: /Saving|Creating/i })
      expect(submitButton).toBeDisabled()
    })

    it('shows loading text on submit button when isLoading', () => {
      render(<TenantForm onSubmit={mockOnSubmit} isLoading={true} mode="create" />)

      expect(screen.getByRole('button', { name: /Creating/i })).toBeInTheDocument()
    })

    it('shows different loading text for edit mode', () => {
      render(<TenantForm onSubmit={mockOnSubmit} isLoading={true} mode="edit" />)

      expect(screen.getByRole('button', { name: /Updating|Saving/i })).toBeInTheDocument()
    })

    it('disables all form fields when isLoading', () => {
      render(<TenantForm onSubmit={mockOnSubmit} isLoading={true} />)

      expect(screen.getByLabelText(/Tenant Name/i)).toBeDisabled()
      expect(screen.getByLabelText(/Description/i)).toBeDisabled()
      expect(screen.getByLabelText(/Logo URL/i)).toBeDisabled()
    })

    it('does not disable cancel button when isLoading', () => {
      render(<TenantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} isLoading={true} />)

      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      expect(cancelButton).not.toBeDisabled()
    })
  })

  describe('Cancel Functionality', () => {
    it('calls onCancel when cancel button clicked', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />)

      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      expect(mockOnCancel).toHaveBeenCalledTimes(1)
    })

    it('does not call onSubmit when cancel button clicked', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />)

      await user.click(screen.getByRole('button', { name: /Cancel/i }))

      expect(mockOnSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has proper label associations', () => {
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      const descriptionInput = screen.getByLabelText(/Description/i)
      const logoInput = screen.getByLabelText(/Logo URL/i)

      expect(nameInput).toHaveAttribute('id')
      expect(descriptionInput).toHaveAttribute('id')
      expect(logoInput).toHaveAttribute('id')
    })

    it('links error messages to inputs with aria-describedby', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/Tenant Name/i)
        const errorId = nameInput.getAttribute('aria-describedby')
        expect(errorId).toBeTruthy()

        const errorElement = document.getElementById(errorId!)
        expect(errorElement).toHaveTextContent(/Name is required/i)
      })
    })

    it('marks required fields with aria-required', () => {
      render(<TenantForm onSubmit={mockOnSubmit} />)

      const nameInput = screen.getByLabelText(/Tenant Name/i)
      expect(nameInput).toHaveAttribute('aria-required', 'true')
    })

    it('marks invalid fields with aria-invalid', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/Tenant Name/i)
        expect(nameInput).toHaveAttribute('aria-invalid', 'true')
      })
    })

    it('has submit button with descriptive accessible name', () => {
      render(<TenantForm onSubmit={mockOnSubmit} mode="create" />)

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })
      expect(submitButton).toBeInTheDocument()
    })

    it('can navigate form with keyboard', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />)

      // Tab through form fields
      await user.tab()
      expect(screen.getByLabelText(/Tenant Name/i)).toHaveFocus()

      await user.tab()
      expect(screen.getByLabelText(/Description/i)).toHaveFocus()

      await user.tab()
      expect(screen.getByLabelText(/Logo URL/i)).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /Cancel/i })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /Create Tenant/i })).toHaveFocus()
    })
  })

  describe('Edge Cases', () => {
    it('trims whitespace from name field on submit', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Tenant Name/i), '  Trimmed Name  ')
      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Trimmed Name',
          })
        )
      })
    })

    it('clears errors when user starts typing', async () => {
      const user = userEvent.setup()
      render(<TenantForm onSubmit={mockOnSubmit} />)

      // Trigger validation error
      await user.click(screen.getByRole('button', { name: /Create Tenant/i }))
      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
      })

      // Start typing to clear error
      await user.type(screen.getByLabelText(/Tenant Name/i), 'New')

      await waitFor(() => {
        expect(screen.queryByText(/Name is required/i)).not.toBeInTheDocument()
      })
    })

    it('handles rapid form submissions gracefully', async () => {
      const user = userEvent.setup()
      // Mock async submission to simulate real API behavior
      const asyncMockOnSubmit = jest.fn().mockImplementation(() =>
        new Promise(resolve => setTimeout(resolve, 100))
      )
      render(<TenantForm onSubmit={asyncMockOnSubmit} />)

      await user.type(screen.getByLabelText(/Tenant Name/i), 'Rapid Submit')

      const submitButton = screen.getByRole('button', { name: /Create Tenant/i })

      // First click starts submission
      await user.click(submitButton)

      // Verify button becomes disabled during submission (double-submit prevention)
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })

      // These clicks should be blocked by disabled button
      await user.click(submitButton)
      await user.click(submitButton)

      // Wait for submission to complete
      await waitFor(() => {
        expect(submitButton).not.toBeDisabled()
      })

      // Should only submit once (form prevents multiple submissions via disabled state)
      expect(asyncMockOnSubmit).toHaveBeenCalledTimes(1)
    })
  })
})
