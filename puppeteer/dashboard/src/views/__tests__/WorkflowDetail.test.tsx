import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';
import { WorkflowDetail } from '../WorkflowDetail';
import * as authModule from '../../auth';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock useNavigate and useParams
const mockNavigate = vi.fn();
const mockParams = {
  id: 'wf-001',
};

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

// Mock DAGCanvas
vi.mock('../../components/DAGCanvas', () => ({
  default: ({ steps, edges, height }: any) => (
    <div data-testid="dag-canvas">
      DAG Canvas: {steps.length} steps, {edges.length} edges, height={height}
    </div>
  ),
}));

describe('WorkflowDetail View', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    mockNavigate.mockClear();
  });

  const renderWorkflowDetail = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <WorkflowDetail />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  it('renders workflow name and cron schedule', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 2,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('Build and Deploy')).toBeInTheDocument();
    expect(screen.getByText('0 2 * * *')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('renders DAG canvas with steps and edges', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 2,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByTestId('dag-canvas')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('DAG canvas receives correct steps and edges', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 2,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    const dagCanvas = screen.getByTestId('dag-canvas');
    expect(dagCanvas).toHaveTextContent('3 steps');
    expect(dagCanvas).toHaveTextContent('2 edges');

    mockFetch.mockRestore();
  });

  it('renders run history table', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 2,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('Run History')).toBeInTheDocument();
    expect(screen.getByText('Started')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('displays run status with correct badge variant', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 2,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    expect(screen.getByText('FAILED')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('calculates and displays run duration', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 2,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    // Wait for the duration to appear in the document
    await waitFor(() => {
      expect(screen.getByText('300.0s')).toBeInTheDocument();
    }, { timeout: 5000 });

    mockFetch.mockRestore();
  });

  it('pagination works for run history', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: sampleRunHistory,
          total: 25,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    const nextButton = screen.getByRole('button', { name: 'Next' });
    expect(nextButton).not.toBeDisabled();

    mockFetch.mockRestore();
  });

  it('clicking a run navigates to run detail page', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: [sampleRunHistory[0]],
          total: 1,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    // Find and click the COMPLETED row
    const completedRow = screen.getByText('COMPLETED').closest('tr');
    if (completedRow) {
      fireEvent.click(completedRow);
    }

    await new Promise((r) => setTimeout(r, 50));

    expect(mockNavigate).toHaveBeenCalledWith('/workflows/wf-001/runs/run-001');

    mockFetch.mockRestore();
  });

  it('handles error when workflow not found', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: false,
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText(/Error:/)).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('shows no runs message when run history is empty', async () => {
    const mockFetch = vi
      .spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sampleWorkflowDetail,
      } as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: [],
          total: 0,
          skip: 0,
          limit: 10,
        }),
      } as any);

    renderWorkflowDetail();

    await new Promise((r) => setTimeout(r, 100));

    expect(screen.getByText('No runs yet.')).toBeInTheDocument();

    mockFetch.mockRestore();
  });
});

/**
 * Sample workflow data for testing WorkflowDetail
 */
export const sampleWorkflowDetail = {
  id: 'wf-001',
  name: 'Build and Deploy',
  steps: [
    {
      id: 'step-1',
      node_type: 'SCRIPT',
      scheduled_job_id: 'job-1',
    },
    {
      id: 'step-2',
      node_type: 'IF_GATE',
      scheduled_job_id: undefined,
    },
    {
      id: 'step-3',
      node_type: 'SCRIPT',
      scheduled_job_id: 'job-2',
    },
  ],
  edges: [
    { from_step_id: 'step-1', to_step_id: 'step-2' },
    { from_step_id: 'step-2', to_step_id: 'step-3' },
  ],
  schedule_cron: '0 2 * * *',
  last_run: {
    id: 'run-001',
    workflow_id: 'wf-001',
    status: 'COMPLETED',
    started_at: '2026-04-16T10:00:00Z',
    completed_at: '2026-04-16T10:05:00Z',
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
        status: 'COMPLETED',
        started_at: '2026-04-16T10:01:00Z',
        completed_at: '2026-04-16T10:02:00Z',
        job_guid: undefined,
      },
      {
        id: 'sr-3',
        workflow_step_id: 'step-3',
        status: 'COMPLETED',
        started_at: '2026-04-16T10:02:00Z',
        completed_at: '2026-04-16T10:05:00Z',
        job_guid: 'job-guid-2',
      },
    ],
  },
};

export const sampleRunHistory = [
  {
    id: 'run-001',
    workflow_id: 'wf-001',
    status: 'COMPLETED',
    started_at: '2026-04-16T10:00:00Z',
    completed_at: '2026-04-16T10:05:00Z',
    step_runs: [],
  },
  {
    id: 'run-002',
    workflow_id: 'wf-001',
    status: 'FAILED',
    started_at: '2026-04-15T10:00:00Z',
    completed_at: '2026-04-15T10:03:00Z',
    step_runs: [],
  },
];
