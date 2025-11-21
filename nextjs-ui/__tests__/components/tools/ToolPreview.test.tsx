import { render, screen, fireEvent } from '@testing-library/react';
import { ToolPreview } from '@/components/tools/ToolPreview';
import type { OpenAPIOperation } from '@/lib/api/tools';

const mockOperations: OpenAPIOperation[] = [
  {
    operationId: 'getUsers',
    method: 'GET',
    path: '/api/users',
    summary: 'Get all users',
    description: 'Retrieves a list of all users in the system',
    parameters: [
      { name: 'page', in: 'query', required: false, description: 'Page number' },
      { name: 'limit', in: 'query', required: false, description: 'Items per page' },
    ],
  },
  {
    operationId: 'createUser',
    method: 'POST',
    path: '/api/users',
    summary: 'Create a new user',
    description: 'Creates a new user with the provided data',
    parameters: [
      { name: 'body', in: 'body', required: true, description: 'User data' },
    ],
  },
  {
    operationId: 'deleteUser',
    method: 'DELETE',
    path: '/api/users/{id}',
    summary: 'Delete user',
    description: null,
    parameters: [
      { name: 'id', in: 'path', required: true, description: 'User ID' },
    ],
  },
];

const mockOnSelectionChange = jest.fn();

describe('ToolPreview', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Empty state', () => {
    it('shows empty message when no operations provided', () => {
      render(
        <ToolPreview
          operations={[]}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('No operations found in spec')).toBeInTheDocument();
    });

    it('does not render table when operations array is empty', () => {
      render(
        <ToolPreview
          operations={[]}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });
  });

  describe('Operations table rendering', () => {
    it('renders all operations in the table', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('getUsers')).toBeInTheDocument();
      expect(screen.getByText('createUser')).toBeInTheDocument();
      expect(screen.getByText('deleteUser')).toBeInTheDocument();
    });

    it('displays HTTP method badges with correct styling', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('GET')).toBeInTheDocument();
      expect(screen.getByText('POST')).toBeInTheDocument();
      expect(screen.getByText('DELETE')).toBeInTheDocument();
    });

    it('displays operation paths', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      // Two operations use /api/users path
      const usersPath = screen.getAllByText('/api/users');
      expect(usersPath.length).toBe(2);
      expect(screen.getByText('/api/users/{id}')).toBeInTheDocument();
    });

    it('displays operation summaries', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('Get all users')).toBeInTheDocument();
      expect(screen.getByText('Create a new user')).toBeInTheDocument();
      expect(screen.getByText('Delete user')).toBeInTheDocument();
    });

    it('shows "No summary" when summary is missing', () => {
      const operationsWithoutSummary: OpenAPIOperation[] = [
        {
          operationId: 'testOp',
          method: 'GET',
          path: '/test',
          summary: '',
          description: null,
          parameters: [],
        },
      ];

      render(
        <ToolPreview
          operations={operationsWithoutSummary}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('No summary')).toBeInTheDocument();
    });

    it('displays parameter counts', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      // Check that parameter counts are displayed
      expect(screen.getByText('2 parameter(s)')).toBeInTheDocument();
      // createUser and deleteUser both have 1 parameter
      const singleParamText = screen.getAllByText('1 parameter(s)');
      expect(singleParamText.length).toBe(2);
    });
  });

  describe('Selection functionality', () => {
    it('renders checkbox for each operation', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      // 1 header checkbox + 3 operation checkboxes
      expect(checkboxes).toHaveLength(4);
    });

    it('calls onSelectionChange when operation checkbox is clicked', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      // Click the first operation checkbox (index 1, since 0 is header)
      fireEvent.click(checkboxes[1]);

      expect(mockOnSelectionChange).toHaveBeenCalledWith(['getUsers']);
    });

    it('shows correct selected count', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={['getUsers', 'createUser']}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('2 of 3 selected')).toBeInTheDocument();
    });

    it('checks checkboxes for selected operations', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={['getUsers', 'deleteUser']}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
      // Skip header checkbox at index 0
      expect(checkboxes[1].checked).toBe(true); // getUsers
      expect(checkboxes[2].checked).toBe(false); // createUser
      expect(checkboxes[3].checked).toBe(true); // deleteUser
    });

    it('deselects operation when already selected checkbox is clicked', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={['getUsers']}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      fireEvent.click(checkboxes[1]); // Click getUsers checkbox

      expect(mockOnSelectionChange).toHaveBeenCalledWith([]);
    });
  });

  describe('Select all functionality', () => {
    it('renders select all checkbox in header', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes[0]).toBeInTheDocument();
    });

    it('checks select all checkbox when all operations are selected', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={['getUsers', 'createUser', 'deleteUser']}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
      expect(checkboxes[0].checked).toBe(true);
    });

    it('sets indeterminate state when some operations are selected', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={['getUsers']}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
      expect(checkboxes[0].indeterminate).toBe(true);
    });

    it('selects all operations when select all checkbox is clicked', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(selectAllCheckbox);

      expect(mockOnSelectionChange).toHaveBeenCalledWith([
        'getUsers',
        'createUser',
        'deleteUser',
      ]);
    });

    it('deselects all operations when all are selected and select all is clicked', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={['getUsers', 'createUser', 'deleteUser']}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(selectAllCheckbox);

      expect(mockOnSelectionChange).toHaveBeenCalledWith([]);
    });
  });

  describe('Expandable rows', () => {
    it('renders expand/collapse button for each operation', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(mockOperations.length);
    });

    it('shows chevron right icon when row is collapsed', () => {
      const { container } = render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      // ChevronRight should be present initially
      const chevronRight = container.querySelector('svg[class*="lucide-chevron-right"]');
      expect(chevronRight).toBeInTheDocument();
    });

    it('expands row details when expand button is clicked', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[0]); // Expand first operation

      // Should show description
      expect(
        screen.getByText('Retrieves a list of all users in the system')
      ).toBeInTheDocument();
    });

    it('collapses row when expand button is clicked again', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[0]); // Expand
      fireEvent.click(expandButtons[0]); // Collapse

      // Description should be hidden
      expect(
        screen.queryByText('Retrieves a list of all users in the system')
      ).not.toBeInTheDocument();
    });

    it('shows description in expanded row', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[0]);

      expect(screen.getByText('Description:')).toBeInTheDocument();
      expect(
        screen.getByText('Retrieves a list of all users in the system')
      ).toBeInTheDocument();
    });

    it('does not show description section when description is null', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[2]); // deleteUser has null description

      // Should show Parameters but not Description
      expect(screen.getByText('Parameters:')).toBeInTheDocument();
      expect(screen.queryByText('Description:')).not.toBeInTheDocument();
    });

    it('shows parameters in expanded row', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[0]); // getUsers

      expect(screen.getByText('Parameters:')).toBeInTheDocument();
      expect(screen.getByText('page')).toBeInTheDocument();
      expect(screen.getByText('limit')).toBeInTheDocument();
      // Both parameters are in "query" location
      const queryBadges = screen.getAllByText('query');
      expect(queryBadges.length).toBeGreaterThan(0);
    });

    it('shows required badge for required parameters', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[2]); // deleteUser has required path param

      expect(screen.getByText('required')).toBeInTheDocument();
    });

    it('shows parameter descriptions', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[0]);

      expect(screen.getByText(/Page number/)).toBeInTheDocument();
      expect(screen.getByText(/Items per page/)).toBeInTheDocument();
    });

    it('can expand multiple rows simultaneously', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const expandButtons = screen.getAllByRole('button');
      fireEvent.click(expandButtons[0]); // Expand getUsers
      fireEvent.click(expandButtons[1]); // Expand createUser

      // Both descriptions should be visible
      expect(
        screen.getByText('Retrieves a list of all users in the system')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Creates a new user with the provided data')
      ).toBeInTheDocument();
    });
  });

  describe('Styling and layout', () => {
    it('applies hover effect to operation rows', () => {
      const { container } = render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const rows = container.querySelectorAll('.hover\\:bg-gray-50');
      expect(rows.length).toBeGreaterThan(0);
    });

    it('uses rounded-lg border for container', () => {
      const { container } = render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const mainContainer = container.querySelector('.rounded-lg');
      expect(mainContainer).toBeInTheDocument();
    });

    it('displays operation paths in monospace font', () => {
      render(
        <ToolPreview
          operations={mockOperations}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      const paths = screen.getAllByText(/\/api\//);
      paths.forEach((path) => {
        expect(path.closest('p')).toHaveClass('font-mono');
      });
    });
  });

  describe('Edge cases', () => {
    it('handles operation with no parameters', () => {
      const operationNoParams: OpenAPIOperation[] = [
        {
          operationId: 'healthCheck',
          method: 'GET',
          path: '/health',
          summary: 'Health check',
          description: 'Returns API health status',
          parameters: [],
        },
      ];

      render(
        <ToolPreview
          operations={operationNoParams}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('0 parameter(s)')).toBeInTheDocument();

      const expandButton = screen.getByRole('button');
      fireEvent.click(expandButton);

      // Should not show Parameters section when no parameters
      expect(screen.queryByText('Parameters:')).not.toBeInTheDocument();
    });

    it('handles operations with long paths', () => {
      const longPathOp: OpenAPIOperation[] = [
        {
          operationId: 'longPath',
          method: 'GET',
          path: '/api/v1/organizations/{orgId}/projects/{projectId}/issues/{issueId}/comments',
          summary: 'Get comments',
          description: null,
          parameters: [],
        },
      ];

      render(
        <ToolPreview
          operations={longPathOp}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(
        screen.getByText(
          '/api/v1/organizations/{orgId}/projects/{projectId}/issues/{issueId}/comments'
        )
      ).toBeInTheDocument();
    });

    it('handles unusual HTTP methods with default badge variant', () => {
      const unusualMethod: OpenAPIOperation[] = [
        {
          operationId: 'patchResource',
          method: 'PATCH',
          path: '/api/resource',
          summary: 'Patch resource',
          description: null,
          parameters: [],
        },
      ];

      render(
        <ToolPreview
          operations={unusualMethod}
          selectedOperations={[]}
          onSelectionChange={mockOnSelectionChange}
        />
      );

      expect(screen.getByText('PATCH')).toBeInTheDocument();
    });
  });
});
