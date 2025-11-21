/**
 * McpServerForm Component Tests
 *
 * Tests for the MCP server creation/configuration form.
 * Covers: field validation, conditional configuration rendering,
 * type selection, checkbox fields, and form submission.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { McpServerForm } from './McpServerForm'

// Mock ConnectionConfig and StdioConfig components
jest.mock('./ConnectionConfig', () => ({
  ConnectionConfig: () => (
    <div data-testid="connection-config">
      <label htmlFor="connection-url">Connection URL</label>
      <input id="connection-url" placeholder="https://example.com" />
      <label htmlFor="connection-timeout">Timeout (ms)</label>
      <input id="connection-timeout" type="number" placeholder="30000" />
    </div>
  ),
}))

jest.mock('./StdioConfig', () => ({
  StdioConfig: () => (
    <div data-testid="stdio-config">
      <label htmlFor="stdio-command">Command</label>
      <input id="stdio-command" placeholder="node server.js" />
      <label htmlFor="stdio-args">Arguments</label>
      <input id="stdio-args" placeholder="--port 3000" />
      <label htmlFor="stdio-env">Environment Variables</label>
      <textarea id="stdio-env" placeholder="KEY=value" />
    </div>
  ),
}))

describe('McpServerForm', () => {
  const mockOnSubmit = jest.fn()

  const defaultProps = {
    onSubmit: mockOnSubmit,
    isSubmitting: false,
    submitLabel: 'Create Server',
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders basic information section', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(screen.getByText('Basic Information')).toBeInTheDocument()
    })

    it('renders all basic fields', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(screen.getByLabelText(/Server Name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Server Type/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Description/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Enable Health Checks/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Active/i)).toBeInTheDocument()
    })

    it('renders submit and reset buttons', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(screen.getByRole('button', { name: /Create Server/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Reset/i })).toBeInTheDocument()
    })

    it('shows required indicators on required fields', () => {
      render(<McpServerForm {...defaultProps} />)

      // Server Type shows required indicator
      expect(screen.getByText(/Server Type/)).toBeInTheDocument()
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('uses custom submit label when provided', () => {
      render(<McpServerForm {...defaultProps} submitLabel="Update Server" />)

      expect(screen.getByRole('button', { name: /Update Server/i })).toBeInTheDocument()
    })
  })

  describe('Basic Field Input', () => {
    it('updates server name when user types', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'My MCP Server')

      expect(nameInput).toHaveValue('My MCP Server')
    })

    it('updates description when user types', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const descInput = screen.getByLabelText(/Description/i)
      await user.type(descInput, 'This server provides data access tools')

      expect(descInput).toHaveValue('This server provides data access tools')
    })

    it('displays correct placeholder for name field', () => {
      render(<McpServerForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Server Name/i)
      expect(nameInput).toHaveAttribute('placeholder', 'My MCP Server')
    })

    it('displays correct placeholder for description field', () => {
      render(<McpServerForm {...defaultProps} />)

      const descInput = screen.getByLabelText(/Description/i)
      expect(descInput).toHaveAttribute(
        'placeholder',
        'Brief description of what this server does'
      )
    })

    it('displays help text for name field', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(
        screen.getByText('A unique, descriptive name for this MCP server')
      ).toBeInTheDocument()
    })
  })

  describe('Type Selection and Help Text', () => {
    it('renders server type dropdown with all options', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(
        screen.getByRole('option', { name: 'HTTP (Stateless)' })
      ).toBeInTheDocument()
      expect(
        screen.getByRole('option', { name: 'SSE (Server-Sent Events)' })
      ).toBeInTheDocument()
      expect(
        screen.getByRole('option', { name: 'stdio (Command-line)' })
      ).toBeInTheDocument()
    })

    it('defaults to HTTP type', () => {
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)
      expect(typeSelect).toHaveValue('http')
    })

    it('shows HTTP help text by default', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(
        screen.getByText('Stateless POST requests to HTTP endpoint')
      ).toBeInTheDocument()
    })

    it('updates help text when selecting SSE', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)
      await user.selectOptions(typeSelect, 'sse')

      expect(
        screen.getByText('Persistent connection using Server-Sent Events')
      ).toBeInTheDocument()
      expect(
        screen.queryByText('Stateless POST requests to HTTP endpoint')
      ).not.toBeInTheDocument()
    })

    it('updates help text when selecting stdio', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)
      await user.selectOptions(typeSelect, 'stdio')

      expect(
        screen.getByText('Local subprocess communication via stdin/stdout')
      ).toBeInTheDocument()
    })

    it('allows changing server type', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)

      await user.selectOptions(typeSelect, 'sse')
      expect(typeSelect).toHaveValue('sse')

      await user.selectOptions(typeSelect, 'stdio')
      expect(typeSelect).toHaveValue('stdio')

      await user.selectOptions(typeSelect, 'http')
      expect(typeSelect).toHaveValue('http')
    })
  })

  describe('Conditional Configuration Components', () => {
    it('shows ConnectionConfig by default (HTTP type)', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(screen.getByTestId('connection-config')).toBeInTheDocument()
      expect(screen.queryByTestId('stdio-config')).not.toBeInTheDocument()
    })

    it('shows ConnectionConfig for SSE type', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)
      await user.selectOptions(typeSelect, 'sse')

      expect(screen.getByTestId('connection-config')).toBeInTheDocument()
      expect(screen.queryByTestId('stdio-config')).not.toBeInTheDocument()
    })

    it('shows StdioConfig when stdio type selected', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)
      await user.selectOptions(typeSelect, 'stdio')

      expect(screen.getByTestId('stdio-config')).toBeInTheDocument()
      expect(screen.queryByTestId('connection-config')).not.toBeInTheDocument()
    })

    it('switches between configs when type changes', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const typeSelect = screen.getByLabelText(/Server Type/i)

      // Start with HTTP (ConnectionConfig)
      expect(screen.getByTestId('connection-config')).toBeInTheDocument()

      // Switch to stdio
      await user.selectOptions(typeSelect, 'stdio')
      expect(screen.getByTestId('stdio-config')).toBeInTheDocument()
      expect(screen.queryByTestId('connection-config')).not.toBeInTheDocument()

      // Switch back to HTTP
      await user.selectOptions(typeSelect, 'http')
      expect(screen.getByTestId('connection-config')).toBeInTheDocument()
      expect(screen.queryByTestId('stdio-config')).not.toBeInTheDocument()
    })
  })

  describe('Checkbox Fields', () => {
    it('health check enabled is checked by default', () => {
      render(<McpServerForm {...defaultProps} />)

      const checkbox = screen.getByLabelText(/Enable Health Checks/i) as HTMLInputElement
      expect(checkbox).toBeChecked()
    })

    it('is active is checked by default', () => {
      render(<McpServerForm {...defaultProps} />)

      const checkbox = screen.getByLabelText(/Active/i) as HTMLInputElement
      expect(checkbox).toBeChecked()
    })

    it('toggles health check checkbox when clicked', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const checkbox = screen.getByLabelText(/Enable Health Checks/i) as HTMLInputElement
      expect(checkbox).toBeChecked()

      await user.click(checkbox)
      expect(checkbox).not.toBeChecked()

      await user.click(checkbox)
      expect(checkbox).toBeChecked()
    })

    it('toggles is active checkbox when clicked', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const checkbox = screen.getByLabelText(/Active/i) as HTMLInputElement
      expect(checkbox).toBeChecked()

      await user.click(checkbox)
      expect(checkbox).not.toBeChecked()

      await user.click(checkbox)
      expect(checkbox).toBeChecked()
    })

    it('shows help text for health check', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(
        screen.getByText('Periodically check server availability and log health status')
      ).toBeInTheDocument()
    })

    it('shows help text for is active', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(
        screen.getByText('Server is active and available for agent use')
      ).toBeInTheDocument()
    })
  })

  describe('Form Submission', () => {
    it('calls onSubmit with form data when submitted', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      // Fill form
      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'Test Server')

      const descInput = screen.getByLabelText(/Description/i)
      await user.type(descInput, 'Test description')

      // Submit
      const submitButton = screen.getByRole('button', { name: /Create Server/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Test Server',
            description: 'Test description',
            type: 'http',
            health_check_enabled: true,
            is_active: true,
          })
        )
      })
    })

    it('includes unchecked checkbox values in submission', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      await user.type(screen.getByLabelText(/Server Name/i), 'Test Server')

      // Uncheck health check
      const healthCheckbox = screen.getByLabelText(/Enable Health Checks/i)
      await user.click(healthCheckbox)

      // Uncheck is active
      const activeCheckbox = screen.getByLabelText(/Active/i)
      await user.click(activeCheckbox)

      await user.click(screen.getByRole('button', { name: /Create Server/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            health_check_enabled: false,
            is_active: false,
          })
        )
      })
    })

    it('resets form after successful submission', async () => {
      const user = userEvent.setup()
      mockOnSubmit.mockResolvedValueOnce(undefined)

      render(<McpServerForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'Test Server')

      expect(nameInput).toHaveValue('Test Server')

      const submitButton = screen.getByRole('button', { name: /Create Server/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(nameInput).toHaveValue('')
      })
    })

    it('handles submission error gracefully', async () => {
      const user = userEvent.setup()
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation()
      mockOnSubmit.mockRejectedValueOnce(new Error('Submission failed'))

      render(<McpServerForm {...defaultProps} />)

      await user.type(screen.getByLabelText(/Server Name/i), 'Test')
      await user.click(screen.getByRole('button', { name: /Create Server/i }))

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Form submission error:',
          expect.any(Error)
        )
      })

      consoleErrorSpy.mockRestore()
    })
  })

  describe('Reset Functionality', () => {
    it('clears all fields when reset clicked', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      // Fill form
      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'Test Server')

      const descInput = screen.getByLabelText(/Description/i)
      await user.type(descInput, 'Test description')

      // Change type
      const typeSelect = screen.getByLabelText(/Server Type/i)
      await user.selectOptions(typeSelect, 'stdio')

      // Uncheck checkboxes
      await user.click(screen.getByLabelText(/Enable Health Checks/i))
      await user.click(screen.getByLabelText(/Active/i))

      // Reset
      const resetButton = screen.getByRole('button', { name: /Reset/i })
      await user.click(resetButton)

      // Verify reset
      await waitFor(() => {
        expect(nameInput).toHaveValue('')
        expect(descInput).toHaveValue('')
        expect(typeSelect).toHaveValue('http')
        expect(screen.getByLabelText(/Enable Health Checks/i)).toBeChecked()
        expect(screen.getByLabelText(/Active/i)).toBeChecked()
      })
    })

    it('resets to default values when provided', async () => {
      const user = userEvent.setup()
      const defaultValues = {
        name: 'Default Server',
        type: 'sse' as const,
        description: 'Default description',
        health_check_enabled: false,
        is_active: false,
        connection_config: {
          url: 'https://example.com',
          timeout: 30000,
          headers: {},
        },
      }

      render(<McpServerForm {...defaultProps} defaultValues={defaultValues} />)

      // Change values
      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.clear(nameInput)
      await user.type(nameInput, 'Changed Server')

      // Reset
      await user.click(screen.getByRole('button', { name: /Reset/i }))

      // Should return to default values
      await waitFor(() => {
        expect(nameInput).toHaveValue('Default Server')
      })
    })
  })

  describe('Validation', () => {
    it('shows error when name is empty on submit', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const submitButton = screen.getByRole('button', { name: /Create Server/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })
    })

    it('clears error when user starts typing', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      // Trigger error
      await user.click(screen.getByRole('button', { name: /Create Server/i }))

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })

      // Start typing
      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'Test')

      await waitFor(() => {
        expect(screen.queryByText(/name is required/i)).not.toBeInTheDocument()
      })
    })

    it('validates minimum name length', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'ab') // Too short

      await user.click(screen.getByRole('button', { name: /Create Server/i }))

      await waitFor(() => {
        expect(screen.getByText(/name must be at least 3 characters/i)).toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    it('disables buttons when isSubmitting is true', () => {
      render(<McpServerForm {...defaultProps} isSubmitting={true} />)

      const submitButton = screen.getByRole('button', { name: /Create Server/i })
      const resetButton = screen.getByRole('button', { name: /Reset/i })

      expect(submitButton).toBeDisabled()
      expect(resetButton).toBeDisabled()
    })

    it('shows spinner in submit button when isSubmitting', () => {
      render(<McpServerForm {...defaultProps} isSubmitting={true} />)

      const submitButton = screen.getByRole('button', { name: /Create Server/i })
      expect(submitButton.querySelector('.animate-spin')).toBeInTheDocument()
    })
  })

  describe('Default Values', () => {
    it('pre-fills form with defaultValues', () => {
      const defaultValues = {
        name: 'Existing Server',
        type: 'stdio' as const,
        description: 'Existing description',
        health_check_enabled: false,
        is_active: false,
        stdio_config: {
          command: 'node',
          args: ['server.js'],
          env: { PORT: '3000' },
        },
      }

      render(<McpServerForm {...defaultProps} defaultValues={defaultValues} />)

      expect(screen.getByLabelText(/Server Name/i)).toHaveValue('Existing Server')
      expect(screen.getByLabelText(/Server Type/i)).toHaveValue('stdio')
      expect(screen.getByLabelText(/Description/i)).toHaveValue('Existing description')
      expect(screen.getByLabelText(/Enable Health Checks/i)).not.toBeChecked()
      expect(screen.getByLabelText(/Active/i)).not.toBeChecked()
    })
  })

  describe('Accessibility', () => {
    it('all form fields have proper labels', () => {
      render(<McpServerForm {...defaultProps} />)

      expect(screen.getByLabelText(/Server Name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Server Type/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Description/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Enable Health Checks/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Active/i)).toBeInTheDocument()
    })

    it('form can be navigated with keyboard', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      await user.tab() // Name field
      expect(screen.getByLabelText(/Server Name/i)).toHaveFocus()

      await user.tab() // Type field
      expect(screen.getByLabelText(/Server Type/i)).toHaveFocus()

      await user.tab() // Description field
      expect(screen.getByLabelText(/Description/i)).toHaveFocus()
    })

    it('submit button can be activated with Enter key', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      await user.type(screen.getByLabelText(/Server Name/i), 'Test Server')

      const submitButton = screen.getByRole('button', { name: /Create Server/i })
      submitButton.focus()
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled()
      })
    })

    it('checkboxes can be toggled with Space key', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const healthCheckbox = screen.getByLabelText(
        /Enable Health Checks/i
      ) as HTMLInputElement
      healthCheckbox.focus()

      expect(healthCheckbox).toBeChecked()

      await user.keyboard(' ') // Space key
      expect(healthCheckbox).not.toBeChecked()
    })
  })

  describe('Edge Cases', () => {
    it('handles very long server name', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const longName = 'A'.repeat(200)
      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, longName)

      expect(nameInput).toHaveValue(longName)
    })

    it('handles whitespace-only name as invalid', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, '   ')

      await user.click(screen.getByRole('button', { name: /Create Server/i }))

      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument()
      })
    })

    it('handles special characters in description', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const specialDesc = 'Server with <special> & "characters"'
      const descInput = screen.getByLabelText(/Description/i)
      await user.type(descInput, specialDesc)

      expect(descInput).toHaveValue(specialDesc)
    })

    it('maintains form state when switching types multiple times', async () => {
      const user = userEvent.setup()
      render(<McpServerForm {...defaultProps} />)

      const nameInput = screen.getByLabelText(/Server Name/i)
      await user.type(nameInput, 'Persistent Server')

      const typeSelect = screen.getByLabelText(/Server Type/i)

      // Rapid type switching
      await user.selectOptions(typeSelect, 'stdio')
      await user.selectOptions(typeSelect, 'sse')
      await user.selectOptions(typeSelect, 'http')

      // Name should persist
      expect(nameInput).toHaveValue('Persistent Server')
    })
  })
})
