/**
 * TestSandbox Component Tests
 *
 * Tests for the agent test execution sandbox component.
 * Covers: input handling, test execution, success/error states,
 * JSON response display, metadata, and accessibility.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TestSandbox } from './TestSandbox'
import * as useTestAgentHook from '@/lib/hooks/useTestAgent'

// Mock @uiw/react-json-view
jest.mock('@uiw/react-json-view', () => ({
  __esModule: true,
  default: ({ value }: { value: object }) => (
    <div data-testid="json-view">{JSON.stringify(value)}</div>
  ),
}))

jest.mock('@uiw/react-json-view/light', () => ({
  lightTheme: {},
}))

jest.mock('@uiw/react-json-view/dark', () => ({
  darkTheme: {},
}))

// Mock useTestAgent hook
jest.mock('@/lib/hooks/useTestAgent')

describe('TestSandbox', () => {
  const mockMutateAsync = jest.fn()
  const mockReset = jest.fn()

  const defaultMutation = {
    mutateAsync: mockMutateAsync,
    isPending: false,
    data: null,
    error: null,
    reset: mockReset,
  }

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue(defaultMutation)
  })

  describe('Rendering', () => {
    it('renders test message textarea', () => {
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      expect(textarea).toBeInTheDocument()
      expect(textarea).toHaveAttribute('placeholder', 'Enter a message to test this agent...')
    })

    it('renders execute test button', () => {
      render(<TestSandbox agentId="agent-1" />)

      const button = screen.getByRole('button', { name: /Execute Test/i })
      expect(button).toBeInTheDocument()
    })

    it('displays label with required indicator', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Test Message')).toBeInTheDocument()
      expect(screen.getByText('(required)')).toBeInTheDocument()
    })

    it('shows empty state initially', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Ready to Test')).toBeInTheDocument()
      expect(
        screen.getByText(/Enter a test message above and click/i)
      ).toBeInTheDocument()
    })
  })

  describe('Input Handling', () => {
    it('updates message value when user types', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Hello agent')

      expect(textarea).toHaveValue('Hello agent')
    })

    it('shows character counter when message is typed', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test')

      expect(screen.getByText('4 characters')).toBeInTheDocument()
    })

    it('updates character counter as user types', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Hello world!')

      expect(screen.getByText('12 characters')).toBeInTheDocument()
    })

    it('does not show character counter when message is empty', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.queryByText(/characters$/)).not.toBeInTheDocument()
    })

    it('allows clearing the message', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test message')
      expect(textarea).toHaveValue('Test message')

      await user.clear(textarea)
      expect(textarea).toHaveValue('')
    })
  })

  describe('Button States', () => {
    it('disables execute button when message is empty', () => {
      render(<TestSandbox agentId="agent-1" />)

      const button = screen.getByRole('button', { name: /Execute Test/i })
      expect(button).toBeDisabled()
    })

    it('disables execute button when message is only whitespace', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, '   ')

      const button = screen.getByRole('button', { name: /Execute Test/i })
      expect(button).toBeDisabled()
    })

    it('enables execute button when message has content', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test message')

      const button = screen.getByRole('button', { name: /Execute Test/i })
      expect(button).toBeEnabled()
    })

    it('disables button and textarea during loading', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        isPending: true,
      })

      render(<TestSandbox agentId="agent-1" />)

      const button = screen.getByRole('button', { name: /Testing agent/i })
      const textarea = screen.getByLabelText(/Test message input/i)

      expect(button).toBeDisabled()
      expect(textarea).toBeDisabled()
    })
  })

  describe('Test Execution', () => {
    it('calls mutateAsync with agentId and message when execute clicked', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test this agent')

      const button = screen.getByRole('button', { name: /Execute Test/i })
      await user.click(button)

      expect(mockMutateAsync).toHaveBeenCalledTimes(1)
      expect(mockMutateAsync).toHaveBeenCalledWith({
        agentId: 'agent-1',
        data: { message: 'Test this agent' },
      })
    })

    it('does not call mutateAsync when message is empty', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      // Button should be disabled, but let's ensure the function doesn't get called
      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'test')
      await user.clear(textarea)

      // Try to click (should be disabled)
      const button = screen.getByRole('button', { name: /Execute Test/i })
      expect(button).toBeDisabled()

      expect(mockMutateAsync).not.toHaveBeenCalled()
    })

    it('does not call mutateAsync when message is whitespace only', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, '   ')

      const button = screen.getByRole('button', { name: /Execute Test/i })
      expect(button).toBeDisabled()

      expect(mockMutateAsync).not.toHaveBeenCalled()
    })

    it('shows loading state during execution', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        isPending: true,
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Testing agent...')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Testing agent/i })).toBeInTheDocument()
    })

    it('displays loader icon during execution', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        isPending: true,
      })

      render(<TestSandbox agentId="agent-1" />)

      // Loader2 component is rendered (has animate-spin class)
      const button = screen.getByRole('button', { name: /Testing agent/i })
      expect(button.querySelector('.animate-spin')).toBeInTheDocument()
    })
  })

  describe('Success State', () => {
    const mockSuccessResult = {
      execution_time_ms: 1234,
      message: 'Success',
      metadata: {
        model: 'gpt-4',
        tokens_used: 150,
      },
      output: {
        response: 'This is the agent response',
        data: { key: 'value' },
      },
    }

    beforeEach(() => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: mockSuccessResult,
      })
    })

    it('displays success banner', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Test Completed Successfully')).toBeInTheDocument()
    })

    it('displays execution time', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('1234')).toBeInTheDocument()
      expect(screen.getByText('ms')).toBeInTheDocument()
    })

    it('displays status message', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Success')).toBeInTheDocument()
    })

    it('displays metadata keys count', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Execution Metadata')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument() // 2 metadata keys
    })

    it('renders JSON view with test result output', () => {
      render(<TestSandbox agentId="agent-1" />)

      const jsonView = screen.getByTestId('json-view')
      expect(jsonView).toBeInTheDocument()
      expect(jsonView).toHaveTextContent('This is the agent response')
    })

    it('displays agent response section', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Agent Response')).toBeInTheDocument()
    })

    it('shows clear results button', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(
        screen.getByRole('button', { name: /Clear Results/i })
      ).toBeInTheDocument()
    })

    it('handles metadata with empty object', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: {
          ...mockSuccessResult,
          metadata: {},
        },
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('handles missing metadata gracefully', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: {
          ...mockSuccessResult,
          metadata: undefined,
        },
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('uses "Success" as fallback status message', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: {
          ...mockSuccessResult,
          message: '',
        },
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Success')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    const mockError = {
      message: 'Agent execution failed: Timeout after 30s',
    }

    beforeEach(() => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        error: mockError,
      })
    })

    it('displays error alert', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('displays error title', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Test Failed')).toBeInTheDocument()
    })

    it('displays error message', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(
        screen.getByText('Agent execution failed: Timeout after 30s')
      ).toBeInTheDocument()
    })

    it('error alert has aria-live assertive', () => {
      render(<TestSandbox agentId="agent-1" />)

      const alert = screen.getByRole('alert')
      expect(alert).toHaveAttribute('aria-live', 'assertive')
    })

    it('error alert shows AlertCircle icon', () => {
      render(<TestSandbox agentId="agent-1" />)

      const alert = screen.getByRole('alert')
      expect(alert.querySelector('.text-destructive')).toBeInTheDocument()
    })

    it('does not show success banner when error exists', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(
        screen.queryByText('Test Completed Successfully')
      ).not.toBeInTheDocument()
    })

    it('does not show JSON response when error exists', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.queryByText('Agent Response')).not.toBeInTheDocument()
      expect(screen.queryByTestId('json-view')).not.toBeInTheDocument()
    })
  })

  describe('Clear Results', () => {
    const mockSuccessResult = {
      execution_time_ms: 1234,
      message: 'Success',
      metadata: {},
      output: { response: 'Test response' },
    }

    it('calls reset mutation when clear results clicked', async () => {
      const user = userEvent.setup()
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: mockSuccessResult,
      })

      render(<TestSandbox agentId="agent-1" />)

      const clearButton = screen.getByRole('button', { name: /Clear Results/i })
      await user.click(clearButton)

      expect(mockReset).toHaveBeenCalledTimes(1)
    })

    it('clears message textarea when clear results clicked', async () => {
      const user = userEvent.setup()
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: mockSuccessResult,
      })

      render(<TestSandbox agentId="agent-1" />)

      // Simulate user having typed a message before
      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Previous test message')

      const clearButton = screen.getByRole('button', { name: /Clear Results/i })
      await user.click(clearButton)

      // After clicking, the message should be cleared
      await waitFor(() => {
        expect(textarea).toHaveValue('')
      })
    })

    it('does not show clear button when no results', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(
        screen.queryByRole('button', { name: /Clear Results/i })
      ).not.toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no results and not loading', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('Ready to Test')).toBeInTheDocument()
      expect(screen.getByRole('img', { name: 'Test tube' })).toBeInTheDocument()
    })

    it('does not show empty state when loading', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        isPending: true,
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.queryByText('Ready to Test')).not.toBeInTheDocument()
    })

    it('does not show empty state when results exist', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: {
          execution_time_ms: 100,
          message: 'Success',
          metadata: {},
          output: {},
        },
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.queryByText('Ready to Test')).not.toBeInTheDocument()
    })

    it('does not show empty state when error exists', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        error: { message: 'Test error' },
      })

      render(<TestSandbox agentId="agent-1" />)

      expect(screen.queryByText('Ready to Test')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('textarea has aria-label', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByLabelText(/Test message input/i)).toBeInTheDocument()
    })

    it('error alert has proper ARIA attributes', () => {
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        error: { message: 'Error occurred' },
      })

      render(<TestSandbox agentId="agent-1" />)

      const alert = screen.getByRole('alert')
      expect(alert).toHaveAttribute('aria-live', 'assertive')
    })

    it('required field is indicated', () => {
      render(<TestSandbox agentId="agent-1" />)

      expect(screen.getByText('(required)')).toBeInTheDocument()
    })

    it('button state changes are keyboard accessible', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      const button = screen.getByRole('button', { name: /Execute Test/i })

      expect(button).toBeDisabled()

      // Type via keyboard
      textarea.focus()
      await user.keyboard('Test message')

      expect(button).toBeEnabled()

      // Clear via keyboard
      await user.clear(textarea)
      expect(button).toBeDisabled()
    })
  })

  describe('Edge Cases', () => {
    it('handles mutation error during execution', async () => {
      const user = userEvent.setup()
      const mockError = new Error('Network error')
      mockMutateAsync.mockRejectedValueOnce(mockError)

      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test')

      const button = screen.getByRole('button', { name: /Execute Test/i })
      await user.click(button)

      // Error is caught and logged
      expect(mockMutateAsync).toHaveBeenCalled()
    })

    it('handles very long message input', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const longMessage = 'A'.repeat(5000)
      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, longMessage)

      expect(textarea).toHaveValue(longMessage)
      expect(screen.getByText('5000 characters')).toBeInTheDocument()
    })

    it('handles rapid execute clicks', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test')

      const button = screen.getByRole('button', { name: /Execute Test/i })

      // Rapid clicks
      await user.click(button)
      await user.click(button)
      await user.click(button)

      // Should only call once (or handle appropriately based on implementation)
      expect(mockMutateAsync).toHaveBeenCalled()
    })

    it('handles special characters in message', async () => {
      const user = userEvent.setup()
      render(<TestSandbox agentId="agent-1" />)

      const specialMessage = '<script>alert("xss")</script> & "quotes" \'apostrophes\''
      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, specialMessage)

      expect(textarea).toHaveValue(specialMessage)
    })

    it('maintains textarea resize functionality', () => {
      render(<TestSandbox agentId="agent-1" />)

      const textarea = screen.getByLabelText(/Test message input/i)
      expect(textarea).toHaveClass('resize-y')
    })
  })

  describe('Integration Scenarios', () => {
    it('completes full success workflow: type, execute, view results, clear', async () => {
      const user = userEvent.setup()
      const mockResult = {
        execution_time_ms: 500,
        message: 'Completed',
        metadata: { tokens: 100 },
        output: { result: 'success' },
      }

      // Start with no results
      render(<TestSandbox agentId="agent-1" />)

      // 1. Type message
      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test this agent')
      expect(textarea).toHaveValue('Test this agent')

      // 2. Execute
      const executeButton = screen.getByRole('button', { name: /Execute Test/i })
      await user.click(executeButton)
      expect(mockMutateAsync).toHaveBeenCalledWith({
        agentId: 'agent-1',
        data: { message: 'Test this agent' },
      })

      // 3. Simulate success
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        data: mockResult,
      })
      rerender(<TestSandbox agentId="agent-1" />)

      // 4. View results
      expect(screen.getByText('Test Completed Successfully')).toBeInTheDocument()
      expect(screen.getByText('500')).toBeInTheDocument()
      expect(screen.getByTestId('json-view')).toBeInTheDocument()

      // 5. Clear
      const clearButton = screen.getByRole('button', { name: /Clear Results/i })
      await user.click(clearButton)
      expect(mockReset).toHaveBeenCalled()
    })

    it('completes full error workflow', async () => {
      const user = userEvent.setup()
      const mockError = { message: 'Agent not found' }

      render(<TestSandbox agentId="agent-1" />)

      // Type and execute
      const textarea = screen.getByLabelText(/Test message input/i)
      await user.type(textarea, 'Test')
      await user.click(screen.getByRole('button', { name: /Execute Test/i }))

      // Simulate error
      ;(useTestAgentHook.useTestAgent as jest.Mock).mockReturnValue({
        ...defaultMutation,
        error: mockError,
      })
      rerender(<TestSandbox agentId="agent-1" />)

      // Verify error display
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Test Failed')).toBeInTheDocument()
      expect(screen.getByText('Agent not found')).toBeInTheDocument()
    })
  })
})
