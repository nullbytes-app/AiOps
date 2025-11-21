/**
 * Unit Tests for CSV Export Utilities
 * Story 15: Agent Performance Dashboard - Error Analysis
 * Testing AC #5: CSV export with correct format and filename
 */

import { exportErrorsToCSV } from '../csv-export';
import type { ErrorAnalysisDTO } from '@/types/agent-performance';

// Mock Papa.unparse
jest.mock('papaparse', () => ({
  unparse: jest.fn(() => {
    // Simple CSV mock - just return stringified data for testing
    return 'Error Type,Error Message,Occurrences,First Seen,Last Seen,Affected Executions,Severity\n' +
      'ValidationError,"Invalid input format",23,2025-01-15T10:30:00Z,2025-01-21T14:22:00Z,23,high';
  }),
}));

describe('exportErrorsToCSV', () => {
  let mockCreateElement: jest.SpyInstance;
  let mockRemoveChild: jest.SpyInstance;
  let mockRevokeObjectURL: jest.SpyInstance;
  let mockClick: jest.Mock;

  beforeEach(() => {
    // Mock DOM methods for download
    mockClick = jest.fn();
    mockCreateElement = jest.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      style: { display: '' },
      click: mockClick,
    } as unknown as HTMLElement);

    jest.spyOn(document.body, 'appendChild').mockImplementation();
    mockRemoveChild = jest.spyOn(document.body, 'removeChild').mockImplementation();

    // Mock URL global methods for Jest environment (not available by default)
    global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
    mockRevokeObjectURL = jest.fn();
    global.URL.revokeObjectURL = mockRevokeObjectURL;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('exports errors to CSV with correct filename format', () => {
    const mockErrors: ErrorAnalysisDTO[] = [
      {
        error_type: 'ValidationError',
        error_message: 'Invalid input format',
        occurrences: 23,
        first_seen: '2025-01-15T10:30:00Z',
        last_seen: '2025-01-21T14:22:00Z',
        affected_executions: 23,
        sample_stack_trace: 'Stack trace here',
        execution_ids: ['exec-123'],
      },
    ];

    const agentId = 'agent-456';
    exportErrorsToCSV(mockErrors, agentId);

    // Verify link element created
    expect(mockCreateElement).toHaveBeenCalledWith('a');

    // Verify download triggered
    expect(mockClick).toHaveBeenCalled();

    // Verify cleanup
    expect(mockRemoveChild).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalled();
  });

  it('generates filename with agent ID and current date', () => {
    const mockErrors: ErrorAnalysisDTO[] = [
      {
        error_type: 'TimeoutError',
        error_message: 'Request timeout',
        occurrences: 8,
        first_seen: '2025-01-18T09:15:00Z',
        last_seen: '2025-01-20T16:45:00Z',
        affected_executions: 8,
        execution_ids: ['exec-234'],
      },
    ];

    const agentId = 'test-agent-789';
    let capturedFilename = '';

    mockCreateElement.mockReturnValue({
      set download(value: string) {
        capturedFilename = value;
      },
      href: '',
      style: { display: '' },
      click: mockClick,
    } as unknown as HTMLElement);

    exportErrorsToCSV(mockErrors, agentId);

    // Filename should be: agent-{agentId}-errors-{YYYY-MM-DD}.csv
    expect(capturedFilename).toMatch(/^agent-test-agent-789-errors-\d{4}-\d{2}-\d{2}\.csv$/);
  });

  it('includes severity level in exported data', () => {
    const mockErrors: ErrorAnalysisDTO[] = [
      {
        error_type: 'LowError',
        error_message: 'Low severity error',
        occurrences: 3, // Should be 'low'
        first_seen: '2025-01-15T10:30:00Z',
        last_seen: '2025-01-15T11:30:00Z',
        affected_executions: 3,
        execution_ids: ['exec-1'],
      },
      {
        error_type: 'MediumError',
        error_message: 'Medium severity error',
        occurrences: 10, // Should be 'medium'
        first_seen: '2025-01-15T10:30:00Z',
        last_seen: '2025-01-15T11:30:00Z',
        affected_executions: 10,
        execution_ids: ['exec-2'],
      },
      {
        error_type: 'HighError',
        error_message: 'High severity error',
        occurrences: 25, // Should be 'high'
        first_seen: '2025-01-15T10:30:00Z',
        last_seen: '2025-01-15T11:30:00Z',
        affected_executions: 25,
        execution_ids: ['exec-3'],
      },
    ];

    exportErrorsToCSV(mockErrors, 'agent-123');

    // Papa.unparse should have been called with data including severity
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Papa = require('papaparse');
    expect(Papa.unparse).toHaveBeenCalled();
  });

  it('creates Blob with correct CSV content type', () => {
    const mockErrors: ErrorAnalysisDTO[] = [
      {
        error_type: 'TestError',
        error_message: 'Test message',
        occurrences: 1,
        first_seen: '2025-01-15T10:30:00Z',
        last_seen: '2025-01-15T11:30:00Z',
        affected_executions: 1,
        execution_ids: ['exec-1'],
      },
    ];

    const originalBlob = global.Blob;
    const mockBlob = jest.fn();
    global.Blob = mockBlob as unknown as typeof Blob;

    exportErrorsToCSV(mockErrors, 'agent-123');

    // Verify Blob created with CSV mime type
    expect(mockBlob).toHaveBeenCalledWith(
      expect.any(Array),
      expect.objectContaining({ type: 'text/csv;charset=utf-8;' })
    );

    global.Blob = originalBlob;
  });
});
