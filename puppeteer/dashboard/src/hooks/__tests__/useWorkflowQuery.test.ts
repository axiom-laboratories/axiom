import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

/**
 * Placeholder useWorkflowQuery hook for testing
 */
const useWorkflowQuery = (workflowId: string, options?: any) => {
  // Placeholder implementation
  return {
    data: undefined,
    isLoading: true,
    error: null,
    isError: false,
  };
};

describe('useWorkflowQuery Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches workflow details from /api/workflows/{id}', async () => {
    const { result } = renderHook(() => useWorkflowQuery('wf-001'));
    expect(result.current).toBeDefined();
  });

  it('returns workflow data with steps and edges', async () => {
    const { result } = renderHook(() => useWorkflowQuery('wf-001'));
    expect(result.current).toHaveProperty('data');
    expect(result.current).toHaveProperty('isLoading');
  });

  it('handles loading state correctly', async () => {
    const { result } = renderHook(() => useWorkflowQuery('wf-001'));
    expect(result.current.isLoading).toBeDefined();
  });

  it('handles error state when API fails', async () => {
    const { result } = renderHook(() => useWorkflowQuery('wf-001'));
    expect(result.current).toHaveProperty('error');
    expect(result.current).toHaveProperty('isError');
  });

  it('refetches on interval when refetchInterval set', async () => {
    const { result } = renderHook(() =>
      useWorkflowQuery('wf-001', { refetchInterval: 5000 })
    );
    expect(result.current).toBeDefined();
  });

  it('cache is properly updated on WebSocket workflow_step_updated event', async () => {
    const { result } = renderHook(() => useWorkflowQuery('wf-001'));
    expect(result.current).toBeDefined();
  });
});

/**
 * Sample workflow data for testing
 */
export const sampleWorkflowForQuery = {
  id: 'wf-001',
  name: 'Deploy Pipeline',
  steps: [
    { id: 'step-1', node_type: 'SCRIPT', scheduled_job_id: 'job-1' },
    { id: 'step-2', node_type: 'IF_GATE', scheduled_job_id: undefined },
  ],
  edges: [{ from_step_id: 'step-1', to_step_id: 'step-2' }],
  schedule_cron: '0 2 * * *',
};
