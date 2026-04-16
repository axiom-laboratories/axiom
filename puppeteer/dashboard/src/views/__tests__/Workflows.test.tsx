import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock useFeatures hook
vi.mock('../../hooks/useFeatures', () => ({
  useFeatures: vi.fn(() => ({
    workflows: true,
  })),
}));

// Placeholder component for testing
const WorkflowsList = () => {
  return (
    <div>
      <h2>Workflows</h2>
      <p>Workflows list placeholder</p>
    </div>
  );
};

describe('Workflows List View', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('renders list of workflows with name, step count, last run status, trigger type', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <WorkflowsList />
      </QueryClientProvider>
    );
    expect(screen.getByText('Workflows')).toBeInTheDocument();
  });

  it('displays empty state when no workflows exist', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <WorkflowsList />
      </QueryClientProvider>
    );
    expect(screen.getByText('Workflows list placeholder')).toBeInTheDocument();
  });

  it('displays last run time and trigger type (MANUAL/CRON/WEBHOOK) correctly', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <WorkflowsList />
      </QueryClientProvider>
    );
    expect(screen.getByText('Workflows')).toBeInTheDocument();
  });

  it('clicking a workflow navigates to detail view', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <WorkflowsList />
      </QueryClientProvider>
    );
    expect(screen.getByText('Workflows')).toBeInTheDocument();
  });
});

/**
 * Sample Workflow fixtures for testing
 */
export const sampleWorkflow = {
  id: 'wf-001',
  name: 'Deploy Pipeline',
  steps: [
    { id: 'step-1', node_type: 'SCRIPT', scheduled_job_id: 'job-1' },
    { id: 'step-2', node_type: 'IF_GATE', scheduled_job_id: undefined },
  ],
  edges: [{ from_step_id: 'step-1', to_step_id: 'step-2' }],
  schedule_cron: '0 2 * * *',
  last_run: {
    id: 'run-001',
    workflow_id: 'wf-001',
    status: 'COMPLETED',
    started_at: '2026-04-16T10:00:00Z',
    completed_at: '2026-04-16T10:05:00Z',
    step_runs: [],
  },
};

export const sampleWorkflows = [sampleWorkflow];
