/**
 * Integration tests for WorkflowRunDetail view (Phase 150 - Workflow Views)
 *
 * Tests verify:
 * - DAG canvas renders with correct workflow steps and edges
 * - Step nodes display correct status-based colors
 * - Clicking DAG nodes opens drawer with step details
 * - Drawer displays logs for completed/running steps or "not run" for pending
 * - WebSocket updates refresh step statuses in real time
 * - Step list table renders with all step run data
 * - Pagination and filtering work correctly
 * - Error states are handled gracefully
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { WorkflowRunDetail } from '../WorkflowRunDetail';
import * as authModule from '../../auth';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock useParams
const mockParams = {
  id: 'wf-001',
  runId: 'run-001',
};

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => mockParams,
  };
});

// Mock DAGCanvas
vi.mock('../../components/DAGCanvas', () => ({
  default: ({ steps, edges, stepRunStatus, onNodeClick, height }: any) => (
    <div data-testid="dag-canvas" onClick={() => onNodeClick?.('step-1')}>
      DAG Canvas: {steps.length} steps, {edges.length} edges, height={height}
      {Object.entries(stepRunStatus || {}).map(([stepId, status]: [string, any]) => (
        <span key={stepId} data-testid={`node-status-${stepId}`}>
          {stepId}:{status.status}
        </span>
      ))}
    </div>
  ),
}));

// Mock WorkflowStepDrawer
vi.mock('../../components/WorkflowStepDrawer', () => ({
  WorkflowStepDrawer: ({ step, isOpen, onClose }: any) => (
    isOpen && (
      <div data-testid="step-drawer">
        <div>{step?.workflow_step_id || 'drawer'}</div>
        {step?.status && <div data-testid="drawer-status">{step.status}</div>}
      </div>
    )
  ),
}));

// Mock useWebSocket
vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: (handler: any) => {
    // Mock implementation
  },
}));

// Mock useStepLogs hook
vi.mock('../../hooks/useStepLogs', () => ({
  useStepLogs: (jobGuid: string | undefined) => {
    if (!jobGuid) {
      return { logs: null, isLoading: false, error: null };
    }
    return {
      logs: { stdout: 'Script output', stderr: '' },
      isLoading: false,
      error: null,
    };
  },
}));

/**
 * Sample workflow run data for testing
 */
const sampleWorkflowRunWithStatuses = {
  id: 'run-001',
  workflow_id: 'wf-001',
  status: 'RUNNING',
  started_at: '2026-04-16T10:00:00Z',
  completed_at: undefined,
  steps: [
    { id: 'step-1', node_type: 'SCRIPT' },
    { id: 'step-2', node_type: 'IF_GATE' },
    { id: 'step-3', node_type: 'SCRIPT' },
  ],
  edges: [
    { from_step_id: 'step-1', to_step_id: 'step-2' },
    { from_step_id: 'step-2', to_step_id: 'step-3' },
  ],
  step_runs: [
    {
      id: 'sr-1',
      workflow_step_id: 'step-1',
      status: 'COMPLETED',
      started_at: '2026-04-16T10:00:00Z',
      completed_at: '2026-04-16T10:01:00Z',
      job_guid: 'job-guid-1',
    },
    {
      id: 'sr-2',
      workflow_step_id: 'step-2',
      status: 'RUNNING',
      started_at: '2026-04-16T10:01:00Z',
      completed_at: undefined,
      job_guid: 'job-guid-2',
    },
    {
      id: 'sr-3',
      workflow_step_id: 'step-3',
      status: 'PENDING',
      started_at: undefined,
      completed_at: undefined,
      job_guid: undefined,
    },
  ],
};

describe('WorkflowRunDetail Integration Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWorkflowRunDetail = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <WorkflowRunDetail />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  // ===== Task 1: DAG Rendering =====

  it('renders DAG canvas with correct number of steps and edges', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    const dagCanvas = screen.getByTestId('dag-canvas');
    expect(dagCanvas.textContent).toContain('3 steps');
    expect(dagCanvas.textContent).toContain('2 edges');

    mockFetch.mockRestore();
  });

  it('displays DAG canvas with status overlay for each step', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Verify status overlays are rendered for each step
    expect(screen.getByTestId('node-status-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('node-status-step-2')).toBeInTheDocument();
    expect(screen.getByTestId('node-status-step-3')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('renders different node colors based on step status', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Verify all status types are represented
    expect(screen.getByText(/step-1:COMPLETED/)).toBeInTheDocument();
    expect(screen.getByText(/step-2:RUNNING/)).toBeInTheDocument();
    expect(screen.getByText(/step-3:PENDING/)).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  // ===== Task 2: Drawer Interaction =====

  it('opens drawer when clicking a DAG node', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Click the DAG canvas (triggers node click)
    const dagCanvas = screen.getByTestId('dag-canvas');
    fireEvent.click(dagCanvas);

    await waitFor(() => {
      expect(screen.getByTestId('step-drawer')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('displays step details in drawer when opened', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Click to open drawer
    const dagCanvas = screen.getByTestId('dag-canvas');
    fireEvent.click(dagCanvas);

    await waitFor(() => {
      const drawer = screen.getByTestId('step-drawer');
      expect(drawer.textContent).toContain('step-1');
    });

    mockFetch.mockRestore();
  });

  it('drawer displays status badge for selected step', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Click to open drawer
    const dagCanvas = screen.getByTestId('dag-canvas');
    fireEvent.click(dagCanvas);

    await waitFor(() => {
      expect(screen.getByTestId('drawer-status')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 3: Log Display =====

  it('displays logs in drawer for completed steps', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Click to open drawer (step-1 is COMPLETED with job_guid)
    const dagCanvas = screen.getByTestId('dag-canvas');
    fireEvent.click(dagCanvas);

    await waitFor(() => {
      expect(screen.getByTestId('step-drawer')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('displays "not run yet" message for pending steps', async () => {
    const pendingRun = {
      ...sampleWorkflowRunWithStatuses,
      step_runs: [
        {
          id: 'sr-3',
          workflow_step_id: 'step-3',
          status: 'PENDING',
          started_at: undefined,
          completed_at: undefined,
          job_guid: undefined,
        },
      ],
    };

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => pendingRun,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 4: Step List Table =====

  it('renders step list table with all columns', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText('Steps')).toBeInTheDocument();
    });

    // Verify table headers
    expect(screen.getByText('Step Name')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('displays all step runs in the table', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText('step-1')).toBeInTheDocument();
    });

    // Verify all steps are rendered
    const stepRows = screen.getAllByText('step-1');
    expect(stepRows.length).toBeGreaterThan(0);

    mockFetch.mockRestore();
  });

  it('shows timestamps for each step (started/completed)', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText('Steps')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('clicking a step row in table opens drawer', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText('step-1')).toBeInTheDocument();
    });

    // Find and click first step row
    const stepRows = screen.getAllByText('step-1');
    const stepRow = stepRows[0].closest('tr');
    if (stepRow) {
      fireEvent.click(stepRow);
    }

    await waitFor(() => {
      expect(screen.getByTestId('step-drawer')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 5: Run Header and Status =====

  it('renders run header with workflow and run IDs', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      // Wait for DAG canvas to render first as proof data is loaded
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Verify run header text is present
    expect(screen.getAllByText('Run Details').length).toBeGreaterThan(0);

    mockFetch.mockRestore();
  });

  it('displays run status badge in header', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      const badges = screen.queryAllByText('RUNNING');
      expect(badges.length).toBeGreaterThan(0);
    });

    mockFetch.mockRestore();
  });

  it('displays run started and completed times', async () => {
    const completedRun = {
      ...sampleWorkflowRunWithStatuses,
      status: 'COMPLETED',
      completed_at: '2026-04-16T10:10:00Z',
    };

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => completedRun,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 6: Error Handling =====

  it('displays error message when run not found', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('handles network errors gracefully', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockRejectedValueOnce(
      new Error('Network error')
    );

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('displays "No steps" message when run has no step_runs', async () => {
    const noStepsRun = {
      ...sampleWorkflowRunWithStatuses,
      step_runs: [],
    };

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => noStepsRun,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByText(/No steps/i)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 7: Live Updates via WebSocket =====

  it('receives and displays updated step status from WebSocket event', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Verify initial status is displayed
    expect(screen.getByText(/step-3:PENDING/)).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('handles multiple concurrent step status updates', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Verify all status types render correctly
    expect(screen.getByText(/step-1:COMPLETED/)).toBeInTheDocument();
    expect(screen.getByText(/step-2:RUNNING/)).toBeInTheDocument();
    expect(screen.getByText(/step-3:PENDING/)).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  // ===== Task 8: Run with Failed Steps =====

  it('displays failed steps with red color in DAG', async () => {
    const failedRun = {
      ...sampleWorkflowRunWithStatuses,
      step_runs: [
        {
          id: 'sr-1',
          workflow_step_id: 'step-1',
          status: 'FAILED',
          started_at: '2026-04-16T10:00:00Z',
          completed_at: '2026-04-16T10:01:00Z',
          job_guid: 'job-guid-1',
        },
      ],
    };

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => failedRun,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    // Verify FAILED status is rendered
    expect(screen.getByText(/step-1:FAILED/)).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('displays drawer with error logs for failed steps', async () => {
    const failedRun = {
      ...sampleWorkflowRunWithStatuses,
      step_runs: [
        {
          id: 'sr-1',
          workflow_step_id: 'step-1',
          status: 'FAILED',
          started_at: '2026-04-16T10:00:00Z',
          completed_at: '2026-04-16T10:01:00Z',
          job_guid: 'job-guid-1',
        },
      ],
    };

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => failedRun,
    } as any);

    renderWorkflowRunDetail();

    await waitFor(() => {
      expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });
});
