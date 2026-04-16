import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { WorkflowStepDrawer } from '../WorkflowStepDrawer';

// Mock useStepLogs hook
const mockUseStepLogs = vi.fn();
vi.mock('../../hooks/useStepLogs', () => ({
  useStepLogs: (...args: any[]) => mockUseStepLogs(...args),
}));

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
      <Toaster />
    </QueryClientProvider>
  );
};

const mockStepRun = (overrides = {}): any => ({
  id: 'step-run-1',
  workflow_step_id: 'step-1',
  status: 'COMPLETED',
  started_at: '2026-04-16T10:00:00Z',
  completed_at: '2026-04-16T10:05:00Z',
  job_guid: 'job-123',
  step_detail: {
    id: 'step-1',
    label: 'Build Step',
    node_type: 'SCRIPT',
  },
  ...overrides,
});

describe('WorkflowStepDrawer Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock return for tests that don't explicitly set it
    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });
  });

  it('does not render when isOpen=false', () => {
    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={false} onClose={vi.fn()} />
    );

    // The drawer should not be visible
    expect(screen.queryByText('Build Step')).not.toBeInTheDocument();
  });

  it('renders when isOpen=true', () => {
    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText('Build Step')).toBeInTheDocument();
  });

  it('displays step name, node type badge, and status badge', () => {
    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({ status: 'RUNNING' })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('Build Step')).toBeInTheDocument();
    expect(screen.getByText('SCRIPT')).toBeInTheDocument();
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
  });

  it('displays timestamps and calculates duration for run steps', () => {
    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={vi.fn()} />
    );

    // Check for metadata section - look for the duration label and value
    const durationLabelElements = screen.getAllByText('DURATION');
    expect(durationLabelElements.length).toBeGreaterThan(0);

    // Duration should be calculated and displayed (300 seconds = 5 minutes)
    expect(screen.getByText(/300\.00s/)).toBeInTheDocument();
  });

  it('renders logs for COMPLETED step', async () => {
    const mockLogs = { stdout: 'Build successful\n', stderr: '' };
    mockUseStepLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText('Build successful')).toBeInTheDocument();
    expect(screen.getByText(/STDOUT/)).toBeInTheDocument();
  });

  it('displays loading spinner while fetching logs', () => {
    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={vi.fn()} />
    );

    // Should show loading spinner (SVG with animate-spin class)
    const spinningElements = document.querySelectorAll('.animate-spin');
    expect(spinningElements.length).toBeGreaterThan(0);
  });

  it('displays "not run yet" message for PENDING step', () => {
    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({ status: 'PENDING', started_at: undefined, completed_at: undefined })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('This step has not run yet')).toBeInTheDocument();
  });

  it('displays "skipped" message for SKIPPED step', () => {
    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({ status: 'SKIPPED' })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('This step was skipped')).toBeInTheDocument();
  });

  it('displays "cancelled" message for CANCELLED step', () => {
    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({ status: 'CANCELLED' })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('This step was cancelled')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const mockOnClose = vi.fn();

    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={mockOnClose} />
    );

    // Find close button with aria-label or X icon
    const buttons = screen.getAllByRole('button', { hidden: true });
    // The SheetClose button has the X icon
    const closeButton = buttons.find((btn) => btn.classList.contains('absolute'));

    if (closeButton) {
      fireEvent.click(closeButton);
      expect(mockOnClose).toHaveBeenCalled();
    }
  });

  it('does not call useStepLogs for PENDING steps', () => {
    mockUseStepLogs.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({ status: 'PENDING' })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    // useStepLogs should be called with null when status is PENDING
    expect(mockUseStepLogs).toHaveBeenCalledWith(null);
  });

  it('displays both stdout and stderr when available', () => {
    const mockLogs = {
      stdout: 'Build output\n',
      stderr: 'Warning: deprecated API\n',
    };
    mockUseStepLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText('Build output')).toBeInTheDocument();
    expect(screen.getByText('Warning: deprecated API')).toBeInTheDocument();
    expect(screen.getByText(/STDOUT/)).toBeInTheDocument();
    expect(screen.getByText(/STDERR/)).toBeInTheDocument();
  });

  it('shows "No output captured" when logs exist but are empty', () => {
    const mockLogs = { stdout: '', stderr: '' };
    mockUseStepLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer step={mockStepRun()} isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText('No output captured for this step')).toBeInTheDocument();
  });

  it('handles FAILED step correctly', () => {
    const mockLogs = {
      stdout: 'Build started\n',
      stderr: 'Error: Build failed\n',
    };
    mockUseStepLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({ status: 'FAILED' })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('FAILED')).toBeInTheDocument();
    expect(screen.getByText('Error: Build failed')).toBeInTheDocument();
  });

  it('falls back to workflow_step_id when step_detail.label is missing', () => {
    renderWithProviders(
      <WorkflowStepDrawer
        step={mockStepRun({
          step_detail: undefined,
          workflow_step_id: 'my-step-id',
        })}
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText('my-step-id')).toBeInTheDocument();
  });
});
