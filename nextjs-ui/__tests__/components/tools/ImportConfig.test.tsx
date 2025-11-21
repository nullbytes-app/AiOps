import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ImportConfig } from '@/components/tools/ImportConfig';
import type { AuthConfig } from '@/lib/api/tools';

const mockOnSubmit = jest.fn();

describe('ImportConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Form rendering', () => {
    it('renders all basic form fields', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      expect(screen.getByLabelText(/Tool Name Prefix/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Base URL/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Authentication Type/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Import Tools/ })).toBeInTheDocument();
    });

    it('shows helper text for name prefix field', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      expect(
        screen.getByText(/Prefix added to operation IDs/)
      ).toBeInTheDocument();
    });

    it('shows helper text for base URL field', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      expect(screen.getByText(/API base URL for tool execution/)).toBeInTheDocument();
    });

    it('marks base URL as required', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      expect(screen.getByLabelText(/Base URL \*/)).toBeInTheDocument();
    });

    it('shows name prefix as optional', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      expect(screen.getByLabelText(/Tool Name Prefix \(Optional\)/)).toBeInTheDocument();
    });
  });

  describe('Authentication type selection', () => {
    it('defaults to "none" authentication type', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/) as HTMLSelectElement;
      expect(select.value).toBe('none');
    });

    it('shows all authentication type options', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/) as HTMLSelectElement;
      const options = Array.from(select.options).map((opt) => opt.value);

      expect(options).toEqual(['none', 'api_key', 'bearer', 'basic']);
    });

    it('does not show auth config fields when auth type is "none"', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      expect(screen.queryByText('API Key Configuration')).not.toBeInTheDocument();
      expect(screen.queryByText('Bearer Token Configuration')).not.toBeInTheDocument();
      expect(screen.queryByText('Basic Authentication')).not.toBeInTheDocument();
    });
  });

  describe('API Key authentication', () => {
    it('shows API Key fields when auth type is "api_key"', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'api_key' } });

      expect(screen.getByText('API Key Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText('Key Name')).toBeInTheDocument();
      expect(screen.getByLabelText('Location')).toBeInTheDocument();
      expect(screen.getByLabelText('API Key Value')).toBeInTheDocument();
    });

    it('defaults API key name to "X-API-Key"', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'api_key' } });

      const keyNameInput = screen.getByLabelText('Key Name') as HTMLInputElement;
      expect(keyNameInput.value).toBe('X-API-Key');
    });

    it('defaults API key location to "header"', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'api_key' } });

      const locationSelect = screen.getByLabelText('Location') as HTMLSelectElement;
      expect(locationSelect.value).toBe('header');
    });

    it('shows header and query location options', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'api_key' } });

      const locationSelect = screen.getByLabelText('Location') as HTMLSelectElement;
      const options = Array.from(locationSelect.options).map((opt) => opt.value);

      expect(options).toEqual(['header', 'query']);
    });

    it('uses password input type for API key value', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'api_key' } });

      const keyValueInput = screen.getByLabelText('API Key Value');
      expect(keyValueInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Bearer Token authentication', () => {
    it('shows Bearer Token field when auth type is "bearer"', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'bearer' } });

      expect(screen.getByText('Bearer Token Configuration')).toBeInTheDocument();
      expect(screen.getByLabelText('Bearer Token')).toBeInTheDocument();
    });

    it('uses password input type for bearer token', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'bearer' } });

      const tokenInput = screen.getByLabelText('Bearer Token');
      expect(tokenInput).toHaveAttribute('type', 'password');
    });

    it('hides API key fields when switching to bearer', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'api_key' } });

      expect(screen.getByText('API Key Configuration')).toBeInTheDocument();

      fireEvent.change(select, { target: { value: 'bearer' } });

      expect(screen.queryByText('API Key Configuration')).not.toBeInTheDocument();
      expect(screen.getByText('Bearer Token Configuration')).toBeInTheDocument();
    });
  });

  describe('Basic Authentication', () => {
    it('shows username and password fields when auth type is "basic"', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'basic' } });

      expect(screen.getByText('Basic Authentication')).toBeInTheDocument();
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
    });

    it('uses text input for username', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'basic' } });

      const usernameInput = screen.getByLabelText('Username');
      expect(usernameInput).not.toHaveAttribute('type', 'password');
    });

    it('uses password input for password', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const select = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(select, { target: { value: 'basic' } });

      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Form validation', () => {
    it('validates base URL is required', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });

      // Try to submit without base URL
      fireEvent.click(submitButton);

      // Button should be disabled due to validation
      expect(submitButton).toBeDisabled();
    });

    it('validates base URL format', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, { target: { value: 'not-a-url' } });
      fireEvent.blur(baseUrlInput);

      await waitFor(() => {
        expect(screen.getByText('Invalid URL')).toBeInTheDocument();
      });
    });

    it('accepts name prefix input within max length', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const prefixInput = screen.getByLabelText(/Tool Name Prefix/) as HTMLInputElement;
      const validPrefix = 'jira_';

      fireEvent.change(prefixInput, { target: { value: validPrefix } });

      await waitFor(() => {
        expect(prefixInput.value).toBe(validPrefix);
      });
    });

    it('enables submit button when base URL is valid', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  describe('Form submission', () => {
    it('submits form with none authentication', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          baseUrl: 'https://api.example.com',
          authConfig: { type: 'none' },
        });
      });
    });

    it('submits form with name prefix when provided', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const prefixInput = screen.getByLabelText(/Tool Name Prefix/);
      fireEvent.change(prefixInput, { target: { value: 'jira_' } });

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          namePrefix: 'jira_',
          baseUrl: 'https://api.example.com',
          authConfig: { type: 'none' },
        });
      });
    });

    it('submits form with API key authentication', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      const authSelect = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(authSelect, { target: { value: 'api_key' } });

      const keyNameInput = screen.getByLabelText('Key Name');
      fireEvent.change(keyNameInput, { target: { value: 'API-Key' } });

      const locationSelect = screen.getByLabelText('Location');
      fireEvent.change(locationSelect, { target: { value: 'header' } });

      const keyValueInput = screen.getByLabelText('API Key Value');
      fireEvent.change(keyValueInput, { target: { value: 'secret123' } });

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          baseUrl: 'https://api.example.com',
          authConfig: {
            type: 'api_key',
            api_key_name: 'API-Key',
            api_key_location: 'header',
            api_key_value: 'secret123',
          },
        });
      });
    });

    it('submits form with bearer token authentication', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      const authSelect = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(authSelect, { target: { value: 'bearer' } });

      const tokenInput = screen.getByLabelText('Bearer Token');
      fireEvent.change(tokenInput, { target: { value: 'bearer_token_123' } });

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          baseUrl: 'https://api.example.com',
          authConfig: {
            type: 'bearer',
            bearer_token: 'bearer_token_123',
          },
        });
      });
    });

    it('submits form with basic authentication', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      const authSelect = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(authSelect, { target: { value: 'basic' } });

      const usernameInput = screen.getByLabelText('Username');
      fireEvent.change(usernameInput, { target: { value: 'admin' } });

      const passwordInput = screen.getByLabelText('Password');
      fireEvent.change(passwordInput, { target: { value: 'password123' } });

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          baseUrl: 'https://api.example.com',
          authConfig: {
            type: 'basic',
            basic_username: 'admin',
            basic_password: 'password123',
          },
        });
      });
    });

    it('omits namePrefix when empty string provided', async () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const baseUrlInput = screen.getByLabelText(/Base URL/);
      fireEvent.change(baseUrlInput, {
        target: { value: 'https://api.example.com' },
      });

      // Leave prefix empty (default)
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Import Tools/ });
        expect(submitButton).not.toBeDisabled();
      });

      const submitButton = screen.getByRole('button', { name: /Import Tools/ });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            baseUrl: 'https://api.example.com',
            authConfig: { type: 'none' },
          })
        );
      });
    });
  });

  describe('Loading state', () => {
    it('disables all inputs when isLoading is true', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} isLoading={true} />);

      expect(screen.getByLabelText(/Tool Name Prefix/)).toBeDisabled();
      expect(screen.getByLabelText(/Base URL/)).toBeDisabled();
      expect(screen.getByLabelText(/Authentication Type/)).toBeDisabled();
    });

    it('disables submit button when isLoading is true', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} isLoading={true} />);

      const submitButton = screen.getByRole('button', { name: /Importing.../ });
      expect(submitButton).toBeDisabled();
    });

    it('shows "Importing..." text when isLoading is true', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} isLoading={true} />);

      expect(
        screen.getByRole('button', { name: /Importing.../ })
      ).toBeInTheDocument();
    });

    it('shows "Import Tools" text when not loading', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} isLoading={false} />);

      expect(
        screen.getByRole('button', { name: /Import Tools/ })
      ).toBeInTheDocument();
    });

    it('disables auth fields when isLoading is true', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} isLoading={true} />);

      const authSelect = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(authSelect, { target: { value: 'api_key' } });

      // Auth fields should still be disabled
      expect(screen.getByLabelText('Key Name')).toBeDisabled();
      expect(screen.getByLabelText('API Key Value')).toBeDisabled();
    });
  });

  describe('Layout and styling', () => {
    it('uses grid layout for form fields', () => {
      const { container } = render(<ImportConfig onSubmit={mockOnSubmit} />);

      const grid = container.querySelector('.grid');
      expect(grid).toBeInTheDocument();
      expect(grid).toHaveClass('md:grid-cols-2');
    });

    it('applies background styling to auth config sections', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const authSelect = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(authSelect, { target: { value: 'api_key' } });

      const configSection = screen.getByText('API Key Configuration').parentElement;
      expect(configSection).toHaveClass('bg-gray-50');
      expect(configSection).toHaveClass('rounded-md');
    });

    it('has border-top on submit button section', () => {
      const { container } = render(<ImportConfig onSubmit={mockOnSubmit} />);

      const buttonSection = container.querySelector('.border-t');
      expect(buttonSection).toBeInTheDocument();
    });
  });

  describe('Placeholders and help text', () => {
    it('shows placeholder for name prefix', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const input = screen.getByLabelText(/Tool Name Prefix/) as HTMLInputElement;
      expect(input).toHaveAttribute('placeholder', 'e.g., jira_');
    });

    it('shows placeholder for base URL', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const input = screen.getByLabelText(/Base URL/) as HTMLInputElement;
      expect(input).toHaveAttribute('placeholder', 'https://api.example.com/v1');
    });

    it('shows placeholder for API key value', () => {
      render(<ImportConfig onSubmit={mockOnSubmit} />);

      const authSelect = screen.getByLabelText(/Authentication Type/);
      fireEvent.change(authSelect, { target: { value: 'api_key' } });

      const input = screen.getByLabelText('API Key Value') as HTMLInputElement;
      expect(input).toHaveAttribute('placeholder', 'Enter API key');
    });
  });
});
