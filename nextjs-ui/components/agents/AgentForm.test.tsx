/**
 * AgentForm Component Tests
 *
 * Tests for agent creation and editing form with LLM configuration.
 * Covers: validation, LLM config, model selection, temperature slider, submission.
 */

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AgentForm } from './AgentForm'
import { Agent } from '@/lib/api/agents'
import * as useLLMProvidersHook from '@/lib/hooks/useLLMProviders'

// Mock the useLLMProviders hook
jest.mock('@/lib/hooks/useLLMProviders')

const mockLLMProviders = [
  {
    id: 'provider-1',
    name: 'OpenAI',
    type: 'openai' as const,
    models: [
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', context_window: 8000 },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', context_window: 128000 },
    ],
  },
  {
    id: 'provider-2',
    name: 'Anthropic',
    type: 'anthropic' as const,
    models: [
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', context_window: 200000 },
    ],
  },
]

describe('AgentForm', () => {
  const mockOnSubmit = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useLLMProvidersHook.useLLMProviders as jest.Mock).mockReturnValue({
      data: mockLLMProviders,
      isLoading: false,
    })
  })

  describe('Basic Information Section', () => {
    it('renders all basic fields in create mode', () => {
      render(<AgentForm onSubmit={mockOnSubmit} mode="create" />)

      expect(screen.getByLabelText(/Agent Name/i)).toHaveValue('')
      expect(screen.getByLabelText(/Agent Type/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/Description/i)).toHaveValue('')
      expect(screen.getByRole('button', { name: /Create Agent/i })).toBeInTheDocument()
    })

    it('validates agent name is required', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('validates agent name minimum length (3 characters)', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'AB')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Name must be at least 3 characters/i)).toBeInTheDocument()
      })
    })

    it('renders all agent type options', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const typeSelect = screen.getByLabelText(/Agent Type/i)
      await user.click(typeSelect)

      await waitFor(() => {
        expect(screen.getByText(/Conversational/i)).toBeInTheDocument()
        expect(screen.getByText(/Task Based/i)).toBeInTheDocument()
        expect(screen.getByText(/Reactive/i)).toBeInTheDocument()
        expect(screen.getByText(/Webhook Triggered/i)).toBeInTheDocument()
      })
    })

    it('accepts optional description field', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'Test Agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a helpful assistant with good vibes')

      // Description is optional - submit without it
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled()
      })
    })
  })

  describe('System Prompt Field', () => {
    it('validates system prompt is required', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'Test Agent')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/System prompt is required/i)).toBeInTheDocument()
      })
    })

    it('validates system prompt minimum length (20 characters)', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/System Prompt/i), 'Short prompt')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/System prompt must be at least 20 characters/i)).toBeInTheDocument()
      })
    })

    it('accepts valid system prompt', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'Test Agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a helpful assistant that provides excellent customer support.')

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled()
      })
    })
  })

  describe('LLM Configuration', () => {
    it('renders LLM provider dropdown with available providers', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const providerSelect = screen.getByLabelText(/LLM Provider/i)
      await user.click(providerSelect)

      await waitFor(() => {
        expect(screen.getByText('OpenAI')).toBeInTheDocument()
        expect(screen.getByText('Anthropic')).toBeInTheDocument()
      })
    })

    it('shows loading state when providers are loading', () => {
      ;(useLLMProvidersHook.useLLMProviders as jest.Mock).mockReturnValue({
        data: [],
        isLoading: true,
      })

      render(<AgentForm onSubmit={mockOnSubmit} />)

      expect(screen.getByText(/Loading providers/i)).toBeInTheDocument()
    })

    it('updates model dropdown when provider selected', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      // Select OpenAI provider
      const providerSelect = screen.getByLabelText(/LLM Provider/i)
      await user.selectOptions(providerSelect, 'provider-1')

      await waitFor(() => {
        const modelSelect = screen.getByLabelText(/Model/i)
        expect(within(modelSelect).getByText('GPT-4o Mini')).toBeInTheDocument()
        expect(within(modelSelect).getByText('GPT-4 Turbo')).toBeInTheDocument()
      })
    })

    it('changes available models when provider changed', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      // Select OpenAI
      await user.selectOptions(screen.getByLabelText(/LLM Provider/i), 'provider-1')
      await waitFor(() => {
        expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument()
      })

      // Change to Anthropic
      await user.selectOptions(screen.getByLabelText(/LLM Provider/i), 'provider-2')
      await waitFor(() => {
        expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument()
        expect(screen.queryByText('GPT-4o Mini')).not.toBeInTheDocument()
      })
    })

    it('validates provider is required', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'Test Agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a helpful assistant for testing purposes.')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Provider is required/i)).toBeInTheDocument()
      })
    })

    it('validates model is required', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'Test Agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a helpful assistant for testing purposes.')
      await user.selectOptions(screen.getByLabelText(/LLM Provider/i), 'provider-1')

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Model is required/i)).toBeInTheDocument()
      })
    })
  })

  describe('Temperature Slider', () => {
    it('renders temperature slider with default value 0.7', () => {
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const temperatureSlider = screen.getByLabelText(/Temperature/i)
      expect(temperatureSlider).toHaveValue('0.7')
    })

    it('allows temperature adjustment from 0 to 1', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const temperatureSlider = screen.getByLabelText(/Temperature/i)

      // Test min value
      await user.clear(temperatureSlider)
      await user.type(temperatureSlider, '0')
      expect(temperatureSlider).toHaveValue('0')

      // Test max value
      await user.clear(temperatureSlider)
      await user.type(temperatureSlider, '1')
      expect(temperatureSlider).toHaveValue('1')

      // Test middle value
      await user.clear(temperatureSlider)
      await user.type(temperatureSlider, '0.5')
      expect(temperatureSlider).toHaveValue('0.5')
    })

    it('validates temperature is within range', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const temperatureSlider = screen.getByLabelText(/Temperature/i)

      await user.clear(temperatureSlider)
      await user.type(temperatureSlider, '1.5')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Temperature must be between 0 and 1/i)).toBeInTheDocument()
      })
    })

    it('shows current temperature value', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const temperatureSlider = screen.getByLabelText(/Temperature/i)
      await user.clear(temperatureSlider)
      await user.type(temperatureSlider, '0.8')

      expect(screen.getByText(/0\.8/)).toBeInTheDocument()
    })
  })

  describe('Max Tokens Field', () => {
    it('accepts valid max tokens value (100-8000)', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const maxTokensInput = screen.getByLabelText(/Max Tokens/i)
      await user.clear(maxTokensInput)
      await user.type(maxTokensInput, '2000')

      expect(maxTokensInput).toHaveValue(2000)
    })

    it('validates max tokens minimum (100)', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const maxTokensInput = screen.getByLabelText(/Max Tokens/i)
      await user.clear(maxTokensInput)
      await user.type(maxTokensInput, '50')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Max tokens must be at least 100/i)).toBeInTheDocument()
      })
    })

    it('validates max tokens maximum (8000)', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const maxTokensInput = screen.getByLabelText(/Max Tokens/i)
      await user.clear(maxTokensInput)
      await user.type(maxTokensInput, '10000')
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Max tokens must be at most 8000/i)).toBeInTheDocument()
      })
    })

    it('is optional (can be left empty)', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      // Fill required fields
      await user.type(screen.getByLabelText(/Agent Name/i), 'Test Agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a helpful assistant for testing purposes.')
      await user.selectOptions(screen.getByLabelText(/LLM Provider/i), 'provider-1')
      await user.selectOptions(screen.getByLabelText(/Model/i), 'gpt-4o-mini')

      // Leave max tokens empty
      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled()
      })
    })
  })

  describe('Active Status Toggle', () => {
    it('renders active status toggle with default true', () => {
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const activeToggle = screen.getByLabelText(/Active/i)
      expect(activeToggle).toBeChecked()
    })

    it('allows toggling active status', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      const activeToggle = screen.getByLabelText(/Active/i)

      await user.click(activeToggle)
      expect(activeToggle).not.toBeChecked()

      await user.click(activeToggle)
      expect(activeToggle).toBeChecked()
    })

    it('submits correct is_active value', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      // Fill required fields
      await user.type(screen.getByLabelText(/Agent Name/i), 'Inactive Agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a helpful assistant for testing purposes.')
      await user.selectOptions(screen.getByLabelText(/LLM Provider/i), 'provider-1')
      await user.selectOptions(screen.getByLabelText(/Model/i), 'gpt-4o-mini')

      // Set to inactive
      const activeToggle = screen.getByLabelText(/Active/i)
      await user.click(activeToggle)

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            is_active: false,
          })
        )
      })
    })
  })

  describe('Edit Mode', () => {
    const mockAgent: Partial<Agent> = {
      id: 'agent-1',
      name: 'Existing Agent',
      type: 'task_based',
      description: 'Test agent for editing',
      system_prompt: 'You are a task-based assistant designed for testing.',
      llm_config: {
        provider_id: 'provider-1',
        model: 'gpt-4o-mini',
        temperature: 0.8,
        max_tokens: 3000,
      },
      is_active: false,
    }

    it('pre-fills form with existing agent data', () => {
      render(<AgentForm onSubmit={mockOnSubmit} defaultValues={mockAgent} mode="edit" />)

      expect(screen.getByLabelText(/Agent Name/i)).toHaveValue('Existing Agent')
      expect(screen.getByLabelText(/Agent Type/i)).toHaveValue('task_based')
      expect(screen.getByLabelText(/Description/i)).toHaveValue('Test agent for editing')
      expect(screen.getByLabelText(/System Prompt/i)).toHaveValue('You are a task-based assistant designed for testing.')
      expect(screen.getByLabelText(/Temperature/i)).toHaveValue('0.8')
      expect(screen.getByLabelText(/Max Tokens/i)).toHaveValue(3000)
      expect(screen.getByLabelText(/Active/i)).not.toBeChecked()
    })

    it('shows Update Agent button in edit mode', () => {
      render(<AgentForm onSubmit={mockOnSubmit} defaultValues={mockAgent} mode="edit" />)

      expect(screen.getByRole('button', { name: /Update Agent/i })).toBeInTheDocument()
    })

    it('submits updated values', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} defaultValues={mockAgent} mode="edit" />)

      // Modify name
      const nameInput = screen.getByLabelText(/Agent Name/i)
      await user.clear(nameInput)
      await user.type(nameInput, 'Updated Agent Name')

      await user.click(screen.getByRole('button', { name: /Update Agent/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Updated Agent Name',
          })
        )
      })
    })
  })

  describe('Form Submission', () => {
    it('submits complete form data with all fields', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByLabelText(/Agent Name/i), 'Complete Agent')
      await user.selectOptions(screen.getByLabelText(/Agent Type/i), 'conversational')
      await user.type(screen.getByLabelText(/Description/i), 'Full test agent')
      await user.type(screen.getByLabelText(/System Prompt/i), 'You are a comprehensive testing assistant with all fields filled.')
      await user.selectOptions(screen.getByLabelText(/LLM Provider/i), 'provider-1')
      await user.selectOptions(screen.getByLabelText(/Model/i), 'gpt-4-turbo')

      const temperatureSlider = screen.getByLabelText(/Temperature/i)
      await user.clear(temperatureSlider)
      await user.type(temperatureSlider, '0.9')

      await user.type(screen.getByLabelText(/Max Tokens/i), '4000')

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          name: 'Complete Agent',
          type: 'conversational',
          description: 'Full test agent',
          system_prompt: 'You are a comprehensive testing assistant with all fields filled.',
          llm_config: {
            provider_id: 'provider-1',
            model: 'gpt-4-turbo',
            temperature: 0.9,
            max_tokens: 4000,
            top_p: undefined,
          },
          tool_ids: [],
          is_active: true,
        })
      })
    })

    it('prevents submission when validation fails', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('disables form fields when isLoading', () => {
      render(<AgentForm onSubmit={mockOnSubmit} isLoading={true} />)

      expect(screen.getByLabelText(/Agent Name/i)).toBeDisabled()
      expect(screen.getByLabelText(/Agent Type/i)).toBeDisabled()
      expect(screen.getByLabelText(/System Prompt/i)).toBeDisabled()
      expect(screen.getByRole('button', { name: /Creating|Saving/i })).toBeDisabled()
    })

    it('shows loading text on submit button', () => {
      render(<AgentForm onSubmit={mockOnSubmit} isLoading={true} mode="create" />)

      expect(screen.getByRole('button', { name: /Creating Agent/i })).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper label associations for all fields', () => {
      render(<AgentForm onSubmit={mockOnSubmit} />)

      expect(screen.getByLabelText(/Agent Name/i)).toHaveAttribute('id')
      expect(screen.getByLabelText(/Agent Type/i)).toHaveAttribute('id')
      expect(screen.getByLabelText(/System Prompt/i)).toHaveAttribute('id')
      expect(screen.getByLabelText(/Temperature/i)).toHaveAttribute('id')
    })

    it('marks required fields with aria-required', () => {
      render(<AgentForm onSubmit={mockOnSubmit} />)

      expect(screen.getByLabelText(/Agent Name/i)).toHaveAttribute('aria-required', 'true')
      expect(screen.getByLabelText(/Agent Type/i)).toHaveAttribute('aria-required', 'true')
      expect(screen.getByLabelText(/System Prompt/i)).toHaveAttribute('aria-required', 'true')
    })

    it('links validation errors with aria-describedby', async () => {
      const user = userEvent.setup()
      render(<AgentForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByRole('button', { name: /Create Agent/i }))

      await waitFor(() => {
        const nameInput = screen.getByLabelText(/Agent Name/i)
        const errorId = nameInput.getAttribute('aria-describedby')
        expect(errorId).toBeTruthy()

        const errorElement = document.getElementById(errorId!)
        expect(errorElement).toHaveTextContent(/Name is required/i)
      })
    })
  })
})
