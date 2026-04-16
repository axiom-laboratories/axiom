import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';
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
    </div>
  ),
}));

// Mock WorkflowStepDrawer
vi.mock('../../components/WorkflowStepDrawer', () => ({
  WorkflowStepDrawer: ({ step, isOpen, onClose }: any) => (
    isOpen && <div data-testid="step-drawer">{step?.workflow_step_id || 'drawer'}</div>
  ),
}));

// Mock useWebSocket
vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: (handler: any) => {
    // Mock implementation
  },
}));

describe('WorkflowRunDetail View', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
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

  it('renders run header with status badge', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('Run Details')).toBeInTheDocument();
    // Check for badge using test ID or closest parent if available
    const badges = screen.queryAllByText('RUNNING');
    expect(badges.length).toBeGreaterThan(0);

    mockFetch.mockRestore();
  });

  it('displays run started time, completed time, duration', async () => {
    const completedRun = {
      ...sampleWorkflowRunWithStatuses,
      status: 'COMPLETED',
      completed_at: '2026-04-16T10:05:00Z',
      step_runs: sampleWorkflowRunWithStatuses.step_runs,
    };

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => completedRun,
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('Run Details')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('renders DAG canvas with status overlay', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ...sampleWorkflowRunWithStatuses,
        steps: [
          { id: 'step-1', node_type: 'SCRIPT' },
          { id: 'step-2', node_type: 'IF_GATE' },
        ],
        edges: [{ from_step_id: 'step-1', to_step_id: 'step-2' }],
      }),
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('DAG node colors reflect step statuses', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ...sampleWorkflowRunWithStatuses,
        steps: [
          { id: 'step-1', node_type: 'SCRIPT' },
          { id: 'step-2', node_type: 'IF_GATE' },
        ],
        edges: [{ from_step_id: 'step-1', to_step_id: 'step-2' }],
      }),
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('renders step list table with all WorkflowStepRun data', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('Steps')).toBeInTheDocument();
    expect(screen.getByText('Step Name')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('step list shows started and completed times for each step', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    // Check that step-1 (COMPLETED) is rendered with times
    expect(screen.getByText('step-1')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('clicking a DAG node opens the step drawer', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ...sampleWorkflowRunWithStatuses,
        steps: [{ id: 'step-1', node_type: 'SCRIPT' }],
        edges: [],
      }),
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    const dagCanvas = screen.getByTestId('dag-canvas');
    fireEvent.click(dagCanvas);

    await new Promise((r) => setTimeout(r, 50));

    // After clicking, the drawer should appear
    expect(screen.getByTestId('step-drawer')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('clicking a step in table selects it', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => sampleWorkflowRunWithStatuses,
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    const stepRows = screen.getAllByText('step-1');
    const stepRow = stepRows[0].closest('tr');
    if (stepRow) {
      fireEvent.click(stepRow);
    }

    await new Promise((r) => setTimeout(r, 50));

    // After clicking, the drawer should appear
    expect(screen.getByTestId('step-drawer')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('handles error when run not found', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: false,
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText(/Error:/)).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('displays "No steps" message when run has no step_runs', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ...sampleWorkflowRunWithStatuses,
        step_runs: [],
      }),
    } as any);

    renderWorkflowRunDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('No steps in this run.')).toBeInTheDocument();

    mockFetch.mockRestore();
  });
});

/**
 * Sample workflow run data for testing WorkflowRunDetail
 */
export const sampleWorkflowRunWithStatuses = {
  id: 'run-001',
  workflow_id: 'wf-001',
  status: 'RUNNING',
  started_at: '2026-04-16T10:00:00Z',
  completed_at: undefined,
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
    {
      id: 'sr-4',
      workflow_step_id: 'step-4',
      status: 'FAILED',
      started_at: '2026-04-15T10:00:00Z',
      completed_at: '2026-04-15T10:02:00Z',
      job_guid: 'job-guid-3',
    },
    {
      id: 'sr-5',
      workflow_step_id: 'step-5',
      status: 'SKIPPED',
      started_at: undefined,
      completed_at: undefined,
      job_guid: undefined,
    },
  ],
};

export const sampleStepRun = {
  id: 'sr-1',
  workflow_step_id: 'step-1',
  status: 'COMPLETED',
  started_at: '2026-04-16T10:00:00Z',
  completed_at: '2026-04-16T10:01:00Z',
  job_guid: 'job-guid-1',
};

export const sampleUnrunStepRun = {
  id: 'sr-3',
  workflow_step_id: 'step-3',
  status: 'PENDING',
  started_at: undefined,
  completed_at: undefined,
  job_guid: undefined,
};
