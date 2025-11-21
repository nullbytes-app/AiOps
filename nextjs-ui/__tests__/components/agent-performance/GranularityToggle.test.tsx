import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GranularityToggle } from '@/components/agent-performance/GranularityToggle';

describe('GranularityToggle', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders hourly and daily tabs', () => {
    render(<GranularityToggle value="hourly" onChange={mockOnChange} />);

    expect(screen.getByText('Hourly')).toBeInTheDocument();
    expect(screen.getByText('Daily')).toBeInTheDocument();
  });

  it('highlights selected granularity (hourly)', () => {
    render(<GranularityToggle value="hourly" onChange={mockOnChange} />);

    const hourlyTab = screen.getByRole('tab', { name: /hourly/i });
    // Headless UI uses aria-selected for selected tabs
    expect(hourlyTab).toHaveAttribute('aria-selected', 'true');
  });

  it('highlights selected granularity (daily)', () => {
    render(<GranularityToggle value="daily" onChange={mockOnChange} />);

    const dailyTab = screen.getByRole('tab', { name: /daily/i });
    // Headless UI uses aria-selected for selected tabs
    expect(dailyTab).toHaveAttribute('aria-selected', 'true');
  });

  it('calls onChange when hourly tab clicked', async () => {
    const user = userEvent.setup();
    render(<GranularityToggle value="daily" onChange={mockOnChange} />);

    const hourlyTab = screen.getByRole('tab', { name: /hourly/i });
    await user.click(hourlyTab);

    expect(mockOnChange).toHaveBeenCalledWith('hourly');
  });

  it('calls onChange when daily tab clicked', async () => {
    const user = userEvent.setup();
    render(<GranularityToggle value="hourly" onChange={mockOnChange} />);

    const dailyTab = screen.getByRole('tab', { name: /daily/i });
    await user.click(dailyTab);

    expect(mockOnChange).toHaveBeenCalledWith('daily');
  });
});
