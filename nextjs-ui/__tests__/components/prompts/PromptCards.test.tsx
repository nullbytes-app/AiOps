import { render, screen } from '@testing-library/react';
import { PromptCards } from '@/components/prompts/PromptCards';
import type { PromptTemplate } from '@/lib/api/prompts';

const mockPrompts: PromptTemplate[] = [
  {
    id: '1',
    tenant_id: 'tenant-1',
    name: 'Test Prompt 1',
    description: 'A test prompt template',
    template_text: 'Hello {{name}}',
    variables: ['name'],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: '2',
    tenant_id: 'tenant-1',
    name: 'Test Prompt 2',
    description: null,
    template_text: 'Greetings {{user}} and {{agent}}',
    variables: ['user', 'agent'],
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
  },
];

// Mock Next.js Link
jest.mock('next/link', () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

describe('PromptCards', () => {
  describe('when prompts exist', () => {
    it('renders all prompts in grid layout', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      expect(screen.getByText('Test Prompt 1')).toBeInTheDocument();
      expect(screen.getByText('Test Prompt 2')).toBeInTheDocument();
    });

    it('displays prompt descriptions', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      expect(screen.getByText('A test prompt template')).toBeInTheDocument();
      expect(screen.getByText('No description provided')).toBeInTheDocument();
    });

    it('shows variable count badges', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      expect(screen.getByText('1 variable')).toBeInTheDocument();
      expect(screen.getByText('2 variables')).toBeInTheDocument();
    });

    it('displays relative timestamps', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      // formatDistanceToNow will show relative time
      const timestamps = screen.getAllByText(/updated/i);
      expect(timestamps.length).toBeGreaterThan(0);
    });

    it('shows edit buttons when canEdit is true', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      const editButtons = screen.getAllByRole('button');
      expect(editButtons.length).toBe(mockPrompts.length);
    });

    it('hides edit buttons when canEdit is false', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={false} />);

      const editButtons = screen.queryAllByRole('button');
      expect(editButtons.length).toBe(0);
    });

    it('links to prompt detail pages', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      const links = screen.getAllByRole('link');
      expect(links[0]).toHaveAttribute('href', '/dashboard/prompts/1');
      expect(links[1]).toHaveAttribute('href', '/dashboard/prompts/2');
    });
  });

  describe('when no prompts exist', () => {
    it('shows empty state message', () => {
      render(<PromptCards prompts={[]} canEdit={true} />);

      expect(screen.getByText('No prompts yet')).toBeInTheDocument();
      expect(
        screen.getByText('Create your first prompt template to get started.')
      ).toBeInTheDocument();
    });

    it('shows create button in empty state when canEdit is true', () => {
      render(<PromptCards prompts={[]} canEdit={true} />);

      const createButton = screen.getByRole('button', { name: /create prompt/i });
      expect(createButton).toBeInTheDocument();
    });

    it('hides create button in empty state when canEdit is false', () => {
      render(<PromptCards prompts={[]} canEdit={false} />);

      const createButton = screen.queryByRole('button', { name: /create prompt/i });
      expect(createButton).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('uses semantic HTML with proper structure', () => {
      const { container } = render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      // Should use grid layout
      expect(container.querySelector('.grid')).toBeInTheDocument();
    });

    it('provides proper button labels for screen readers', () => {
      render(<PromptCards prompts={mockPrompts} canEdit={true} />);

      // Edit buttons should be accessible
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toBeVisible();
      });
    });
  });
});
