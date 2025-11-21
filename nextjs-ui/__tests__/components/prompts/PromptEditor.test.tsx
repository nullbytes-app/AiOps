import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PromptEditor } from '@/components/prompts/PromptEditor';
import * as promptsApi from '@/lib/api/prompts';

// Mock CodeMirror
jest.mock('@uiw/react-codemirror', () => ({
  __esModule: true,
  default: ({
    value,
    onChange,
    placeholder,
  }: {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
  }) => (
    <textarea
      data-testid="codemirror-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  ),
}));

// Mock extractVariables function
jest.mock('@/lib/api/prompts', () => ({
  extractVariables: jest.fn((template: string) => {
    const regex = /\{\{(\w+)\}\}/g;
    const matches = Array.from(template.matchAll(regex));
    return Array.from(new Set(matches.map((m) => m[1])));
  }),
}));

const mockOnChange = jest.fn();
const mockOnSave = jest.fn();
const mockOnRevert = jest.fn();

describe('PromptEditor', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Editor rendering', () => {
    it('renders CodeMirror editor with provided value', () => {
      const template = 'Hello {{name}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      const editor = screen.getByTestId('codemirror-editor');
      expect(editor).toHaveValue(template);
    });

    it('displays template editor label', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.getByText('Template Editor')).toBeInTheDocument();
    });

    it('shows placeholder when editor is empty', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      const editor = screen.getByTestId('codemirror-editor');
      expect(editor).toHaveAttribute('placeholder');
    });
  });

  describe('Variable extraction', () => {
    it('detects and displays variables from template', async () => {
      const template = 'Hello {{name}}, your ticket is {{ticket_id}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Detected variables:/)).toBeInTheDocument();
        expect(screen.getByText(/name, ticket_id/)).toBeInTheDocument();
      });
    });

    it('updates detected variables when template changes', async () => {
      const { rerender } = render(
        <PromptEditor
          value="Hello {{name}}"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/Detected variables:/)).toBeInTheDocument();
        expect(screen.getByText(/name/)).toBeInTheDocument();
      });

      rerender(
        <PromptEditor
          value="Hello {{name}}, ticket {{ticket_id}}"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/name, ticket_id/)).toBeInTheDocument();
      });
    });

    it('does not show detected variables section when no variables exist', () => {
      render(
        <PromptEditor
          value="Hello world"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.queryByText(/Detected variables:/)).not.toBeInTheDocument();
    });

    it('handles duplicate variables correctly', async () => {
      const template = 'Hello {{name}}, goodbye {{name}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        // Should only show "name" once
        const detectedText = screen.getByText(/Detected variables:/);
        expect(detectedText.textContent).toBe('Detected variables: name');
      });
    });
  });

  describe('Test data inputs', () => {
    it('renders input fields for each detected variable', async () => {
      const template = 'Hello {{name}}, ticket {{ticket_id}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByLabelText('name')).toBeInTheDocument();
        expect(screen.getByLabelText('ticket_id')).toBeInTheDocument();
      });
    });

    it('updates test data when input values change', async () => {
      const template = 'Hello {{name}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByLabelText('name')).toBeInTheDocument();
      });

      const input = screen.getByLabelText('name') as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'John Doe' } });

      expect(input.value).toBe('John Doe');
    });

    it('does not render test data section when no variables exist', () => {
      render(
        <PromptEditor
          value="No variables here"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.queryByText('Test Variables:')).not.toBeInTheDocument();
    });
  });

  describe('Preview rendering', () => {
    it('displays preview pane with label', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.getByText('Preview with Test Data')).toBeInTheDocument();
      expect(screen.getByText('Rendered Output:')).toBeInTheDocument();
    });

    it('shows placeholder text when template is empty', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.getByText('Start typing to see preview...')).toBeInTheDocument();
    });

    it('displays template in preview when no variables', async () => {
      const template = 'Hello world, no variables here!';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        const preview = screen.getByText(template);
        expect(preview).toBeInTheDocument();
      });
    });

    it('substitutes variables with test data in preview', async () => {
      const template = 'Hello {{name}}, your ticket is {{ticket_id}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByLabelText('name')).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText('name');
      const ticketInput = screen.getByLabelText('ticket_id');

      fireEvent.change(nameInput, { target: { value: 'John Doe' } });
      fireEvent.change(ticketInput, { target: { value: 'TICK-123' } });

      await waitFor(() => {
        expect(
          screen.getByText('Hello John Doe, your ticket is TICK-123')
        ).toBeInTheDocument();
      });
    });

    it('shows placeholder for variables without test data', async () => {
      const template = 'Hello {{name}}';
      render(
        <PromptEditor
          value={template}
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        // When no test data provided, should show {{name}} in preview
        expect(screen.getByText('Hello {{name}}')).toBeInTheDocument();
      });
    });
  });

  describe('Save and Revert buttons', () => {
    it('renders Save button', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
    });

    it('calls onSave when Save button is clicked', () => {
      render(
        <PromptEditor
          value="Test template"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      const saveButton = screen.getByRole('button', { name: 'Save' });
      fireEvent.click(saveButton);

      expect(mockOnSave).toHaveBeenCalledTimes(1);
    });

    it('shows "Saving..." text when isSubmitting is true', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
          isSubmitting={true}
        />
      );

      expect(screen.getByRole('button', { name: 'Saving...' })).toBeInTheDocument();
    });

    it('disables Save button when isSubmitting is true', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
          isSubmitting={true}
        />
      );

      const saveButton = screen.getByRole('button', { name: 'Saving...' });
      expect(saveButton).toBeDisabled();
    });

    it('renders Revert button when onRevert is provided', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
          onRevert={mockOnRevert}
        />
      );

      expect(screen.getByRole('button', { name: 'Revert' })).toBeInTheDocument();
    });

    it('does not render Revert button when onRevert is not provided', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      expect(screen.queryByRole('button', { name: 'Revert' })).not.toBeInTheDocument();
    });

    it('calls onRevert when Revert button is clicked', () => {
      render(
        <PromptEditor
          value="Test template"
          onChange={mockOnChange}
          onSave={mockOnSave}
          onRevert={mockOnRevert}
        />
      );

      const revertButton = screen.getByRole('button', { name: 'Revert' });
      fireEvent.click(revertButton);

      expect(mockOnRevert).toHaveBeenCalledTimes(1);
    });

    it('disables Revert button when isSubmitting is true', () => {
      render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
          onRevert={mockOnRevert}
          isSubmitting={true}
        />
      );

      const revertButton = screen.getByRole('button', { name: 'Revert' });
      expect(revertButton).toBeDisabled();
    });
  });

  describe('Editor interaction', () => {
    it('calls onChange when editor value changes', () => {
      render(
        <PromptEditor
          value="Initial value"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      const editor = screen.getByTestId('codemirror-editor');
      fireEvent.change(editor, { target: { value: 'New value' } });

      expect(mockOnChange).toHaveBeenCalledWith('New value');
    });

    it('updates preview in real-time as template changes', async () => {
      const { rerender } = render(
        <PromptEditor
          value="Hello {{name}}"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByLabelText('name')).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText('name');
      fireEvent.change(nameInput, { target: { value: 'John' } });

      await waitFor(() => {
        expect(screen.getByText('Hello John')).toBeInTheDocument();
      });

      // Change template
      rerender(
        <PromptEditor
          value="Goodbye {{name}}"
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Goodbye John')).toBeInTheDocument();
      });
    });
  });

  describe('Layout and structure', () => {
    it('uses split-pane layout with correct structure', () => {
      const { container } = render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      // Should have flex layout for split panes
      const mainContainer = container.firstChild as HTMLElement;
      expect(mainContainer).toHaveClass('flex');
      expect(mainContainer).toHaveClass('flex-col');
      expect(mainContainer).toHaveClass('md:flex-row');
    });

    it('has proper responsive classes for mobile and desktop', () => {
      const { container } = render(
        <PromptEditor
          value=""
          onChange={mockOnChange}
          onSave={mockOnSave}
        />
      );

      const mainContainer = container.firstChild as HTMLElement;
      const editorPane = mainContainer.children[0] as HTMLElement;
      const previewPane = mainContainer.children[1] as HTMLElement;

      // Editor pane should take 60% on desktop
      expect(editorPane).toHaveClass('md:w-3/5');
      // Preview pane should take 40% on desktop
      expect(previewPane).toHaveClass('md:w-2/5');
    });
  });
});
