import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Tabs } from '@/components/ui/Tabs';
import '@testing-library/jest-dom';
import { Home, Settings } from 'lucide-react';

describe('Tabs Component', () => {
  const mockTabs = [
    {
      key: 'tab1',
      label: 'Tab 1',
      content: <div>Content 1</div>,
    },
    {
      key: 'tab2',
      label: 'Tab 2',
      content: <div>Content 2</div>,
    },
    {
      key: 'tab3',
      label: 'Tab 3',
      content: <div>Content 3</div>,
    },
  ];

  describe('Rendering', () => {
    it('should render all tab labels', () => {
      render(<Tabs tabs={mockTabs} />);

      expect(screen.getByText('Tab 1')).toBeInTheDocument();
      expect(screen.getByText('Tab 2')).toBeInTheDocument();
      expect(screen.getByText('Tab 3')).toBeInTheDocument();
    });

    it('should render first tab content by default', () => {
      render(<Tabs tabs={mockTabs} />);

      expect(screen.getByText('Content 1')).toBeInTheDocument();
      expect(screen.queryByText('Content 2')).not.toBeInTheDocument();
      expect(screen.queryByText('Content 3')).not.toBeInTheDocument();
    });

    it('should render tab with icon', () => {
      const tabsWithIcons = [
        { key: 'home', label: 'Home', content: <div>Home</div>, icon: <Home data-testid="home-icon" /> },
        { key: 'settings', label: 'Settings', content: <div>Settings</div>, icon: <Settings data-testid="settings-icon" /> },
      ];

      render(<Tabs tabs={tabsWithIcons} />);

      expect(screen.getByTestId('home-icon')).toBeInTheDocument();
      expect(screen.getByTestId('settings-icon')).toBeInTheDocument();
    });

    it('should render disabled tab', () => {
      const tabsWithDisabled = [
        { key: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
        { key: 'tab2', label: 'Tab 2', content: <div>Content 2</div>, disabled: true },
      ];

      render(<Tabs tabs={tabsWithDisabled} />);

      const disabledTab = screen.getByText('Tab 2').closest('button');
      expect(disabledTab).toHaveClass('opacity-50', 'cursor-not-allowed');
      expect(disabledTab).toBeDisabled();
    });
  });

  describe('Interaction', () => {
    it('should switch to second tab when clicked', async () => {
      const user = userEvent.setup();

      render(<Tabs tabs={mockTabs} />);

      expect(screen.getByText('Content 1')).toBeInTheDocument();

      await user.click(screen.getByText('Tab 2'));

      expect(screen.getByText('Content 2')).toBeInTheDocument();
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument();
    });

    it('should call onChange when tab is clicked', async () => {
      const user = userEvent.setup();
      const mockOnChange = jest.fn();

      render(<Tabs tabs={mockTabs} onChange={mockOnChange} />);

      await user.click(screen.getByText('Tab 2'));

      expect(mockOnChange).toHaveBeenCalledWith(1);
    });

    it('should not switch to disabled tab', async () => {
      const user = userEvent.setup();
      const mockOnChange = jest.fn();

      const tabsWithDisabled = [
        { key: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
        { key: 'tab2', label: 'Tab 2', content: <div>Content 2</div>, disabled: true },
      ];

      render(<Tabs tabs={tabsWithDisabled} onChange={mockOnChange} />);

      await user.click(screen.getByText('Tab 2'));

      expect(mockOnChange).not.toHaveBeenCalled();
      expect(screen.getByText('Content 1')).toBeInTheDocument();
    });
  });

  describe('Controlled Mode', () => {
    it('should use controlled selectedIndex', () => {
      render(<Tabs tabs={mockTabs} selectedIndex={1} />);

      expect(screen.getByText('Content 2')).toBeInTheDocument();
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument();
    });

    it('should update when selectedIndex prop changes', () => {
      const { rerender } = render(<Tabs tabs={mockTabs} selectedIndex={0} />);

      expect(screen.getByText('Content 1')).toBeInTheDocument();

      rerender(<Tabs tabs={mockTabs} selectedIndex={2} />);

      expect(screen.getByText('Content 3')).toBeInTheDocument();
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument();
    });
  });

  describe('Default Index', () => {
    it('should start at defaultIndex', () => {
      render(<Tabs tabs={mockTabs} defaultIndex={2} />);

      expect(screen.getByText('Content 3')).toBeInTheDocument();
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument();
    });

    it('should allow user to change from defaultIndex', async () => {
      const user = userEvent.setup();

      render(<Tabs tabs={mockTabs} defaultIndex={1} />);

      expect(screen.getByText('Content 2')).toBeInTheDocument();

      await user.click(screen.getByText('Tab 1'));

      expect(screen.getByText('Content 1')).toBeInTheDocument();
      expect(screen.queryByText('Content 2')).not.toBeInTheDocument();
    });
  });

  describe('Variants', () => {
    it('should apply pills variant classes', () => {
      const { container } = render(<Tabs tabs={mockTabs} variant="pills" />);

      const tabList = container.querySelector('[role="tablist"]');
      expect(tabList).toHaveClass('bg-gray-100', 'dark:bg-gray-800', 'p-1', 'rounded-xl');
    });

    it('should apply underline variant classes', () => {
      const { container } = render(<Tabs tabs={mockTabs} variant="underline" />);

      const tabList = container.querySelector('[role="tablist"]');
      expect(tabList).toHaveClass('border-b', 'border-gray-200', 'dark:border-gray-700');
    });

    it('should apply boxed variant classes', () => {
      const { container } = render(<Tabs tabs={mockTabs} variant="boxed" />);

      const tabList = container.querySelector('[role="tablist"]');
      expect(tabList).toHaveClass('bg-gray-50', 'dark:bg-gray-900', 'border');
    });
  });

  describe('Full Width', () => {
    it('should apply full-width layout when fullWidth is true', () => {
      const { container } = render(<Tabs tabs={mockTabs} fullWidth={true} />);

      const tabButtons = container.querySelectorAll('[role="tab"]');
      tabButtons.forEach((tab) => {
        expect(tab).toHaveClass('flex-1');
      });
    });

    it('should NOT apply full-width layout when fullWidth is false', () => {
      const { container } = render(<Tabs tabs={mockTabs} fullWidth={false} />);

      const tabButtons = container.querySelectorAll('[role="tab"]');
      tabButtons.forEach((tab) => {
        expect(tab).not.toHaveClass('flex-1');
      });
    });
  });

  describe('Accessibility', () => {
    it('should have role="tablist" on tab list', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      expect(container.querySelector('[role="tablist"]')).toBeInTheDocument();
    });

    it('should have role="tab" on tab buttons', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      const tabs = container.querySelectorAll('[role="tab"]');
      expect(tabs).toHaveLength(3);
    });

    it('should have role="tabpanel" on tab panel', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      expect(container.querySelector('[role="tabpanel"]')).toBeInTheDocument();
    });

    it('should set aria-selected on active tab', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      const tabs = container.querySelectorAll('[role="tab"]');
      expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
      expect(tabs[1]).toHaveAttribute('aria-selected', 'false');
    });

    it('should navigate tabs with arrow keys', async () => {
      const user = userEvent.setup();

      render(<Tabs tabs={mockTabs} />);

      // Focus first tab
      const firstTab = screen.getByText('Tab 1').closest('button');
      if (firstTab) {
        firstTab.focus();
      }

      // Press ArrowRight to move to second tab
      await user.keyboard('{ArrowRight}');

      expect(screen.getByText('Content 2')).toBeInTheDocument();

      // Press ArrowRight to move to third tab
      await user.keyboard('{ArrowRight}');

      expect(screen.getByText('Content 3')).toBeInTheDocument();
    });

    it('should focus tabs with Tab key', async () => {
      const user = userEvent.setup();

      render(<Tabs tabs={mockTabs} />);

      await user.tab();

      const firstTab = screen.getByText('Tab 1').closest('button');
      expect(firstTab).toHaveFocus();
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className to container', () => {
      const { container } = render(
        <Tabs tabs={mockTabs} className="custom-class" />
      );

      expect(container.firstChild).toHaveClass('custom-class');
    });

    it('should apply glass-card class to tab panels', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      const panel = container.querySelector('[role="tabpanel"]');
      expect(panel).toHaveClass('glass-card');
    });
  });

  describe('Focus Management', () => {
    it('should have focus styles on tabs', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      const tabs = container.querySelectorAll('[role="tab"]');
      tabs.forEach((tab) => {
        if (!tab.getAttribute('disabled')) {
          expect(tab).toHaveClass('focus:outline-none', 'focus:ring-2');
        }
      });
    });

    it('should have focus styles on tab panels', () => {
      const { container } = render(<Tabs tabs={mockTabs} />);

      const panel = container.querySelector('[role="tabpanel"]');
      expect(panel).toHaveClass('focus:outline-none', 'focus:ring-2');
    });
  });
});
