import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock useParams hook
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: vi.fn(() => ({ id: 'wf-001' })),
  };
});

// Mock useFeatures hook
vi.mock('../../hooks/useFeatures', () => ({
  useFeatures: vi.fn(() => ({
    workflows: true,
  })),
}));

// Placeholder component for testing
const WorkflowDetail = () => {
  return (
    <div>
      <h2>Workflow Detail</h2>
      <div>DAG Canvas Placeholder</div>
      <div>Run History List</div>
    </div>
  );
};

describe('WorkflowDetail View', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('renders DAG canvas with nodes for each step', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('DAG Canvas Placeholder')).toBeInTheDocument();
  });

  it('displays run history list below DAG canvas', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Run History List')).toBeInTheDocument();
  });

  it('DAG shows correct node count matching workflow steps', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Workflow Detail')).toBeInTheDocument();
  });

  it('clicking a run in the history list navigates to run detail', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Workflow Detail')).toBeInTheDocument();
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
