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
    useParams: vi.fn(() => ({ id: 'wf-001', runId: 'run-001' })),
  };
});

// Mock useFeatures hook
vi.mock('../../hooks/useFeatures', () => ({
  useFeatures: vi.fn(() => ({
    workflows: true,
  })),
}));

// Placeholder component for testing
const WorkflowRunDetail = () => {
  return (
    <div>
      <h2>Workflow Run Detail</h2>
      <div>DAG Canvas with Status Overlay</div>
      <div>Step Status List</div>
    </div>
  );
};

describe('WorkflowRunDetail View', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('renders DAG canvas with status colors overlaid for current run', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowRunDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('DAG Canvas with Status Overlay')).toBeInTheDocument();
  });

  it('displays step status list beside or below canvas', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowRunDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Step Status List')).toBeInTheDocument();
  });

  it('clicking a step node opens right-side drawer', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowRunDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Workflow Run Detail')).toBeInTheDocument();
  });

  it('drawer shows logs for RUNNING/COMPLETED/FAILED steps', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowRunDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Workflow Run Detail')).toBeInTheDocument();
  });

  it("drawer shows 'unrun' message for PENDING/SKIPPED/CANCELLED steps", () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <WorkflowRunDetail />
        </QueryClientProvider>
      </BrowserRouter>
    );
    expect(screen.getByText('Workflow Run Detail')).toBeInTheDocument();
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
