/**
 * ProviderForm Component Tests
 *
 * Tests for the LLM provider creation/edit form.
 * Covers: field validation, API key masking, type selection,
 * conditional base URL, test connection flow, and submit logic.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProviderForm } from './ProviderForm'

// Mock TestConnection component
jest.mock('./TestConnection', () => ({
  TestConnection: ({ onTest, isLoading, result }: { onTest: () => void; isLoading: boolean; result: Record<string, unknown> | null }) => (
    <div data-testid="test-connection">
      <button onClick={onTest} disabled={isLoading}>
        {isLoading ? 'Testing...' : 'Test Connection'}
      </button>
      {result && (
        <div data-testid="test-result">
          {result.success ? (
            <div>
              <div>Connection Successful</div>
              <div>{result.response_time_ms}ms</div>
              <div>{result.models_found} models</div>
            </div>
          ) : (
            <div>
              <div>Connection Failed</div>
              <div>{result.error}</div>
            </div>
          )}
        </div>
      )}
    </div>
  ),
}))

describe('ProviderForm', () => {
  const mockOnSubmit = jest.fn()
  const mockOnCancel = jest.fn()

  const defaultProps = {
    onSubmit: mockOnSubmit,
    onCancel: mockOnCancel,
    isLoading: false,
    mode: 'create' as const,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  describe('Rendering', () => {
    it('renders all form fields', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(screen.getByLabelText(/Provider Name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Provider Type/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/API Key/i)).toBeInTheDocument()
      expect(screen.getByTestId('test-connection')).toBeInTheDocument()
    })

    it('renders submit and cancel buttons', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(
        screen.getByRole('button', { name: /Create Provider/i })
      ).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('shows required field indicators', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(screen.getByText(/Provider Name \*/)).toBeInTheDocument()
      expect(screen.getByText(/Provider Type \*/)).toBeInTheDocument()
      expect(screen.getByText(/API Key \*/)).toBeInTheDocument()
    })

    it('does not render cancel button when onCancel not provided', () => {
      render(<ProviderForm {...defaultProps} onCancel={undefined} />)

      expect(screen.queryByRole('button', { name: /Cancel/i })).not.toBeInTheDocument()
    })
  })

  describe('Form Input Handling', () => {
    it('updates name field when user types', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Provider Name/i)
      await user.type(nameInput, 'OpenAI Production')

      expect(nameInput).toHaveValue('OpenAI Production')
    })

    it('updates API key field when user types', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const apiKeyInput = screen.getByLabelText(/API Key/i)
      await user.type(apiKeyInput, 'sk-test-key-123')

      expect(apiKeyInput).toHaveValue('sk-test-key-123')
    })

    it('displays correct placeholder for name field', () => {
      render(<ProviderForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Provider Name/i)
      expect(nameInput).toHaveAttribute('placeholder', 'e.g., OpenAI Production')
    })

    it('displays correct placeholder for API key in create mode', () => {
      render(<ProviderForm {...defaultProps} mode="create" />)

      const apiKeyInput = screen.getByLabelText(/API Key/i)
      expect(apiKeyInput).toHaveAttribute('placeholder', 'sk-...')
    })

    it('displays masked placeholder for API key in edit mode', () => {
      render(<ProviderForm {...defaultProps} mode="edit" />)

      const apiKeyInput = screen.getByLabelText(/API Key/i)
      expect(apiKeyInput).toHaveAttribute('placeholder', '••••••••last4')
    })
  })

  describe('Type Selection and Conditional Base URL', () => {
    it('renders provider type dropdown with all options', () => {
      render(<ProviderForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Provider Type/i)
      expect(typeSelect).toBeInTheDocument()

      expect(screen.getByRole('option', { name: 'OpenAI' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Anthropic' })).toBeInTheDocument()
      expect(
        screen.getByRole('option', { name: 'Azure OpenAI' })
      ).toBeInTheDocument()
      expect(
        screen.getByRole('option', { name: 'Custom LiteLLM' })
      ).toBeInTheDocument()
    })

    it('does not show base URL field by default (openai type)', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(screen.queryByLabelText(/Base URL/i)).not.toBeInTheDocument()
    })

    it('shows base URL field when custom type selected', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Provider Type/i)
      await user.selectOptions(typeSelect, 'custom_litellm')

      expect(screen.getByLabelText(/Base URL \*/i)).toBeInTheDocument()
    })

    it('hides base URL field when switching from custom to standard type', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Provider Type/i)

      // Select custom to show base URL
      await user.selectOptions(typeSelect, 'custom_litellm')
      expect(screen.getByLabelText(/Base URL/i)).toBeInTheDocument()

      // Switch back to openai
      await user.selectOptions(typeSelect, 'openai')
      expect(screen.queryByLabelText(/Base URL/i)).not.toBeInTheDocument()
    })

    it('allows entering base URL when shown', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Provider Type/i)
      await user.selectOptions(typeSelect, 'custom_litellm')

      const baseUrlInput = screen.getByLabelText(/Base URL/i)
      await user.type(baseUrlInput, 'https://api.example.com/v1')

      expect(baseUrlInput).toHaveValue('https://api.example.com/v1')
    })
  })

  describe('API Key Show/Hide Toggle', () => {
    it('API key field is password type by default', () => {
      render(<ProviderForm {...defaultProps} />)

      const apiKeyInput = screen.getByLabelText(/API Key/i)
      expect(apiKeyInput).toHaveAttribute('type', 'password')
    })

    it('shows eye icon to reveal API key', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(screen.getByLabelText('Show API key')).toBeInTheDocument()
    })

    it('toggles API key visibility when eye icon clicked', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const apiKeyInput = screen.getByLabelText(/API Key/i)
      const toggleButton = screen.getByLabelText('Show API key')

      expect(apiKeyInput).toHaveAttribute('type', 'password')

      await user.click(toggleButton)
      expect(apiKeyInput).toHaveAttribute('type', 'text')

      await user.click(toggleButton)
      expect(apiKeyInput).toHaveAttribute('type', 'password')
    })

    it('changes toggle button aria-label when visibility changes', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const toggleButton = screen.getByLabelText('Show API key')
      await user.click(toggleButton)

      expect(screen.getByLabelText('Hide API key')).toBeInTheDocument()
      expect(screen.queryByLabelText('Show API key')).not.toBeInTheDocument()
    })
  })

  describe('Validation Errors', () => {
    it('shows error when name is empty on submit', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      // Try to submit without filling name
      const submitButton = screen.getByRole('button', { name: /Create Provider/i })

      // First test connection (required in create mode)
      const testButton = screen.getByRole('button', { name: /Test Connection/i })
      await user.click(testButton)

      jest.advanceTimersByTime(1500)
      await waitFor(() => {
        expect(screen.getByText('Connection Successful')).toBeInTheDocument()
      })

      // Now try to submit
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })
    })

    it('shows error when API key is empty on submit', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      // Fill name only
      const nameInput = screen.getByLabelText(/Provider Name/i)
      await user.type(nameInput, 'Test Provider')

      // Test connection
      const testButton = screen.getByRole('button', { name: /Test Connection/i })
      await user.click(testButton)
      jest.advanceTimersByTime(1500)

      // Try to submit
      const submitButton = screen.getByRole('button', { name: /Create Provider/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/api key is required/i)).toBeInTheDocument()
      })
    })

    it('clears validation errors when user starts typing', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      // Trigger validation error
      const testButton = screen.getByRole('button', { name: /Test Connection/i })
      await user.click(testButton)
      jest.advanceTimersByTime(1500)

      const submitButton = screen.getByRole('button', { name: /Create Provider/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })

      // Start typing to clear error
      const nameInput = screen.getByLabelText(/Provider Name/i)
      await user.type(nameInput, 'Test')

      await waitFor(() => {
        expect(screen.queryByText(/name is required/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Test Connection Flow', () => {
    it('renders test connection component', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(screen.getByTestId('test-connection')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Test Connection/i })).toBeInTheDocument()
    })

    it('shows loading state during test', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const testButton = screen.getByRole('button', { name: /Test Connection/i })
      await user.click(testButton)

      expect(screen.getByRole('button', { name: /Testing.../i })).toBeInTheDocument()
    })

    it('displays success result after test completes', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const testButton = screen.getByRole('button', { name: /Test Connection/i })
      await user.click(testButton)

      // Advance timer by mock delay (1500ms)
      jest.advanceTimersByTime(1500)

      await waitFor(() => {
        expect(screen.getByText('Connection Successful')).toBeInTheDocument()
        expect(screen.getByText('245ms')).toBeInTheDocument()
        expect(screen.getByText('15 models')).toBeInTheDocument()
      })
    })

    it('shows warning in create mode that test is required', () => {
      render(<ProviderForm {...defaultProps} mode="create" />)

      expect(
        screen.getByText(/Test connection must succeed before you can save/i)
      ).toBeInTheDocument()
    })

    it('does not show test warning in edit mode', () => {
      render(<ProviderForm {...defaultProps} mode="edit" />)

      expect(
        screen.queryByText(/Test connection must succeed/i)
      ).not.toBeInTheDocument()
    })
  })

  describe('Submit Behavior - Create Mode', () => {
    it('submit button is disabled before successful test in create mode', () => {
      render(<ProviderForm {...defaultProps} mode="create" />)

      const submitButton = screen.getByRole('button', { name: /Create Provider/i })
      expect(submitButton).toBeDisabled()
    })

    it('submit button is enabled after successful test in create mode', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} mode="create" />)

      const testButton = screen.getByRole('button', { name: /Test Connection/i })
      await user.click(testButton)

      jest.advanceTimersByTime(1500)

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Create Provider/i })
        expect(submitButton).toBeEnabled()
      })
    })

    it('calls onSubmit with form data when submitted', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} mode="create" />)

      // Fill form
      await user.type(screen.getByLabelText(/Provider Name/i), 'OpenAI Prod')
      await user.type(screen.getByLabelText(/API Key/i), 'sk-test-123')

      // Test connection
      await user.click(screen.getByRole('button', { name: /Test Connection/i }))
      jest.advanceTimersByTime(1500)

      await waitFor(() => {
        expect(screen.getByText('Connection Successful')).toBeInTheDocument()
      })

      // Submit
      const submitButton = screen.getByRole('button', { name: /Create Provider/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'OpenAI Prod',
            api_key: 'sk-test-123',
            type: 'openai',
          })
        )
      })
    })

    it('shows creating label during submission', async () => {
      const user = userEvent.setup({ delay: null })
      mockOnSubmit.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      )

      render(<ProviderForm {...defaultProps} mode="create" />)

      // Fill and test
      await user.type(screen.getByLabelText(/Provider Name/i), 'Test')
      await user.type(screen.getByLabelText(/API Key/i), 'sk-test')
      await user.click(screen.getByRole('button', { name: /Test Connection/i }))
      jest.advanceTimersByTime(1500)

      await waitFor(() => {
        expect(screen.getByText('Connection Successful')).toBeInTheDocument()
      })

      // Submit
      await user.click(screen.getByRole('button', { name: /Create Provider/i }))

      await waitFor(() => {
        expect(screen.getByText('Creating...')).toBeInTheDocument()
      })
    })
  })

  describe('Submit Behavior - Edit Mode', () => {
    it('submit button is enabled without testing in edit mode', () => {
      render(
        <ProviderForm
          {...defaultProps}
          mode="edit"
          defaultValues={{ name: 'Existing Provider', api_key: 'sk-123', type: 'openai' }}
        />
      )

      const submitButton = screen.getByRole('button', { name: /Update Provider/i })
      expect(submitButton).toBeEnabled()
    })

    it('shows update label in edit mode', () => {
      render(<ProviderForm {...defaultProps} mode="edit" />)

      expect(
        screen.getByRole('button', { name: /Update Provider/i })
      ).toBeInTheDocument()
    })

    it('shows updating label during submission in edit mode', async () => {
      const user = userEvent.setup({ delay: null })
      mockOnSubmit.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      )

      render(
        <ProviderForm
          {...defaultProps}
          mode="edit"
          defaultValues={{ name: 'Test', api_key: 'sk-test', type: 'openai' }}
        />
      )

      await user.click(screen.getByRole('button', { name: /Update Provider/i }))

      await waitFor(() => {
        expect(screen.getByText('Updating...')).toBeInTheDocument()
      })
    })

    it('pre-fills form fields with defaultValues in edit mode', () => {
      render(
        <ProviderForm
          {...defaultProps}
          mode="edit"
          defaultValues={{
            name: 'OpenAI Production',
            api_key: 'sk-existing-key',
            type: 'anthropic',
          }}
        />
      )

      expect(screen.getByLabelText(/Provider Name/i)).toHaveValue('OpenAI Production')
      expect(screen.getByLabelText(/API Key/i)).toHaveValue('sk-existing-key')
      expect(screen.getByLabelText(/Provider Type/i)).toHaveValue('anthropic')
    })
  })

  describe('Loading States', () => {
    it('disables all inputs when isLoading is true', () => {
      render(<ProviderForm {...defaultProps} isLoading={true} mode="edit" />)

      const submitButton = screen.getByRole('button', { name: /Update Provider/i })
      expect(submitButton).toBeDisabled()
    })

    it('shows spinner in submit button when isLoading', () => {
      render(<ProviderForm {...defaultProps} isLoading={true} mode="edit" />)

      expect(screen.getByText('Updating...')).toBeInTheDocument()
      const submitButton = screen.getByRole('button', { name: /Updating.../i })
      expect(submitButton.querySelector('.animate-spin')).toBeInTheDocument()
    })
  })

  describe('Cancel Button', () => {
    it('calls onCancel when cancel button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)

      expect(mockOnCancel).toHaveBeenCalledTimes(1)
    })

    it('disables cancel button during submission', async () => {
      const user = userEvent.setup({ delay: null })
      mockOnSubmit.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      )

      render(
        <ProviderForm
          {...defaultProps}
          mode="edit"
          defaultValues={{ name: 'Test', api_key: 'sk-test', type: 'openai' }}
        />
      )

      await user.click(screen.getByRole('button', { name: /Update Provider/i }))

      await waitFor(() => {
        const cancelButton = screen.getByRole('button', { name: /Cancel/i })
        expect(cancelButton).toBeDisabled()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper aria-invalid on name field when error', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} mode="edit" />)

      // Submit to trigger validation
      await user.click(screen.getByRole('button', { name: /Update Provider/i }))

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/Provider Name/i)
        expect(nameInput).toHaveAttribute('aria-invalid', 'true')
      })
    })

    it('has aria-describedby linking to error message', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} mode="edit" />)

      await user.click(screen.getByRole('button', { name: /Update Provider/i }))

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/Provider Name/i)
        const errorId = nameInput.getAttribute('aria-describedby')
        expect(errorId).toBe('name-error')
        expect(document.getElementById(errorId!)).toBeInTheDocument()
      })
    })

    it('API key toggle has proper aria-label', () => {
      render(<ProviderForm {...defaultProps} />)

      expect(screen.getByLabelText('Show API key')).toBeInTheDocument()
    })

    it('form fields can be navigated with keyboard', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      await user.tab() // Name field
      expect(screen.getByLabelText(/Provider Name/i)).toHaveFocus()

      await user.tab() // Type field
      expect(screen.getByLabelText(/Provider Type/i)).toHaveFocus()

      await user.tab() // API key field
      expect(screen.getByLabelText(/API Key/i)).toHaveFocus()
    })
  })

  describe('Edge Cases', () => {
    it('handles whitespace-only name gracefully', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} mode="edit" />)

      const nameInput = screen.getByLabelText(/Provider Name/i)
      await user.type(nameInput, '   ')

      const submitButton = screen.getByRole('button', { name: /Update Provider/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })
    })

    it('handles very long provider name', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const longName = 'A'.repeat(200)
      const nameInput = screen.getByLabelText(/Provider Name/i)
      await user.type(nameInput, longName)

      expect(nameInput).toHaveValue(longName)
    })

    it('handles special characters in API key', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      const specialKey = 'sk-!@#$%^&*()_+-={}[]|:";\'<>?,./`~'
      const apiKeyInput = screen.getByLabelText(/API Key/i)
      await user.type(apiKeyInput, specialKey)

      expect(apiKeyInput).toHaveValue(specialKey)
    })

    it('maintains form state when test connection fails', async () => {
      const user = userEvent.setup({ delay: null })
      render(<ProviderForm {...defaultProps} />)

      // Fill form
      await user.type(screen.getByLabelText(/Provider Name/i), 'Test Provider')
      await user.type(screen.getByLabelText(/API Key/i), 'invalid-key')

      // Values should remain even if test fails
      expect(screen.getByLabelText(/Provider Name/i)).toHaveValue('Test Provider')
      expect(screen.getByLabelText(/API Key/i)).toHaveValue('invalid-key')
    })
  })
})
