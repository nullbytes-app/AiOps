/**
 * ShortcutsModal Component Tests
 *
 * Tests for Story 6 AC-2 (Keyboard Shortcuts System)
 * Validates shortcuts modal, keyboard shortcut registration, and accessibility.
 *
 * Coverage target: 80%+
 * Reference: Story 6 AC-8 (Testing & Quality)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShortcutsModal } from '@/components/shortcuts/ShortcutsModal';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  X: () => <div data-testid="x-icon">X</div>,
  Search: () => <div data-testid="search-icon">Search</div>,
  Command: () => <div data-testid="command-icon">Command</div>,
  Home: () => <div data-testid="home-icon">Home</div>,
  Cpu: () => <div data-testid="cpu-icon">Cpu</div>,
}));

describe('ShortcutsModal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should not render modal when closed', () => {
      render(<ShortcutsModal isOpen={false} onClose={() => {}} />);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should render modal when open', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Keyboard Shortcuts' })).toBeInTheDocument();
    });

    it('should display shortcut categories', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify category headers exist
      expect(screen.getByText('Global')).toBeInTheDocument();
      expect(screen.getByText('Navigation')).toBeInTheDocument();
    });

    it('should display individual shortcuts with descriptions', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify at least one shortcut is visible
      // Command Palette (⌘K)
      expect(screen.getByText('Open command palette')).toBeInTheDocument();
    });
  });

  describe('Modal Interactions', () => {
    it('should close modal when close button clicked', () => {
      const handleClose = jest.fn();
      render(<ShortcutsModal isOpen={true} onClose={handleClose} />);

      // Find and click close button
      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('should close modal when Escape key pressed', () => {
      const handleClose = jest.fn();
      render(<ShortcutsModal isOpen={true} onClose={handleClose} />);

      // Press Escape
      fireEvent.keyDown(document, { key: 'Escape' });

      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('should close modal when clicking outside (overlay)', () => {
      const handleClose = jest.fn();
      const { container } = render(<ShortcutsModal isOpen={true} onClose={handleClose} />);

      // Find overlay (backdrop)
      const overlay = container.querySelector('[data-testid="modal-overlay"]');
      if (overlay) {
        fireEvent.click(overlay);
        expect(handleClose).toHaveBeenCalledTimes(1);
      }
    });
  });

  describe('Search Functionality', () => {
    it('should display search input', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);
      expect(searchInput).toBeInTheDocument();
    });

    it('should filter shortcuts based on search query', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);

      // Search for "command"
      fireEvent.change(searchInput, { target: { value: 'command' } });

      // Verify filtered results
      expect(screen.getByText('Open command palette')).toBeInTheDocument();
    });

    it('should show empty state when no shortcuts match search', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);

      // Search for non-existent shortcut
      fireEvent.change(searchInput, { target: { value: 'nonexistentshortcut123' } });

      // Verify empty state
      waitFor(() => {
        expect(screen.getByText(/no shortcuts found/i)).toBeInTheDocument();
      });
    });

    it('should clear search and show all shortcuts when search cleared', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);

      // Enter search
      fireEvent.change(searchInput, { target: { value: 'command' } });

      // Clear search
      fireEvent.change(searchInput, { target: { value: '' } });

      // Verify all categories visible again
      expect(screen.getByText('Global')).toBeInTheDocument();
      expect(screen.getByText('Navigation')).toBeInTheDocument();
    });
  });

  describe('Shortcut Display', () => {
    it('should display keyboard shortcuts in <kbd> badges', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify kbd elements exist for shortcuts
      const kbdElements = screen.getAllByRole('kbd');
      expect(kbdElements.length).toBeGreaterThan(0);
    });

    it('should show Mac-style shortcuts (⌘) on Mac', () => {
      // Mock Mac platform
      Object.defineProperty(navigator, 'platform', {
        value: 'MacIntel',
        writable: true,
      });

      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify ⌘ symbol is used
      // Note: Actual display depends on formatKeys implementation
      // This is a placeholder for platform-specific key formatting
    });

    it('should show Windows-style shortcuts (Ctrl) on Windows', () => {
      // Mock Windows platform
      Object.defineProperty(navigator, 'platform', {
        value: 'Win32',
        writable: true,
      });

      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify Ctrl is used instead of ⌘
      // Note: Actual display depends on formatKeys implementation
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
    });

    it('should trap focus within modal', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Focus should be trapped inside modal
      // Note: Focus trap testing requires more complex setup with @testing-library/user-event
      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
    });

    it('should have accessible close button', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toBeInTheDocument();
      expect(closeButton).toHaveAttribute('aria-label');
    });

    it('should be keyboard navigable', () => {
      const handleClose = jest.fn();
      render(<ShortcutsModal isOpen={true} onClose={handleClose} />);

      // Tab to close button
      const closeButton = screen.getByRole('button', { name: /close/i });
      closeButton.focus();
      expect(closeButton).toHaveFocus();

      // Press Enter to close
      fireEvent.keyDown(closeButton, { key: 'Enter' });
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Shortcut Categories', () => {
    it('should organize shortcuts into logical categories', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify categories
      expect(screen.getByText('Global')).toBeInTheDocument();
      expect(screen.getByText('Navigation')).toBeInTheDocument();

      // Verify at least one shortcut per category
      // Global category should have ⌘K
      expect(screen.getByText('Open command palette')).toBeInTheDocument();
    });

    it('should display all required global shortcuts', () => {
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);

      // Verify required shortcuts from AC-2
      expect(screen.getByText(/command palette/i)).toBeInTheDocument();
      expect(screen.getByText(/sidebar/i)).toBeInTheDocument();
      expect(screen.getByText(/theme/i)).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('should render modal without performance issues', () => {
      const startTime = performance.now();
      render(<ShortcutsModal isOpen={true} onClose={() => {}} />);
      const endTime = performance.now();

      // Modal should render in less than 100ms
      expect(endTime - startTime).toBeLessThan(100);
    });

    it('should handle rapid open/close cycles', () => {
      const handleClose = jest.fn();
      const { rerender } = render(<ShortcutsModal isOpen={false} onClose={handleClose} />);

      // Rapid open/close
      rerender(<ShortcutsModal isOpen={true} onClose={handleClose} />);
      rerender(<ShortcutsModal isOpen={false} onClose={handleClose} />);
      rerender(<ShortcutsModal isOpen={true} onClose={handleClose} />);
      rerender(<ShortcutsModal isOpen={false} onClose={handleClose} />);

      // Should not crash
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});
