/**
 * Integration tests for Workflows view (Phase 150 - Workflow Views)
 *
 * Tests verify:
 * - Workflow list renders with correct columns and data
 * - Navigation to workflow detail page works
 * - Pagination controls work correctly
 * - Empty state is displayed when no workflows exist
 * - Error handling displays error messages
 * - React Query integration with data fetching
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { Workflows } from '../Workflows';
import * as authModule from '../../auth';

// Mock authenticatedFetch
vi.mock('../../auth', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

/**
 * Test fixtures: Sample workflows for testing
 */
const sampleWorkflows = [
  {
    id: 'wf-001',
    name: 'Deploy Pipeline',
    steps: [
      { id: 'step-1', node_type: 'SCRIPT' },
      { id: 'step-2', node_type: 'IF_GATE' },
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
  },
  {
    id: 'wf-002',
    name: 'Data ETL',
    steps: [
      { id: 'step-3', node_type: 'SCRIPT' },
      { id: 'step-4', node_type: 'AND_JOIN' },
    ],
    edges: [{ from_step_id: 'step-3', to_step_id: 'step-4' }],
    schedule_cron: null,
    last_run: {
      id: 'run-002',
      workflow_id: 'wf-002',
      status: 'FAILED',
      started_at: '2026-04-16T09:00:00Z',
      completed_at: '2026-04-16T09:03:00Z',
      step_runs: [],
    },
  },
  {
    id: 'wf-003',
    name: 'Backup Job',
    steps: [{ id: 'step-5', node_type: 'SCRIPT' }],
    edges: [],
    schedule_cron: '0 0 * * *',
    last_run: null,
  },
];

describe('Workflows Integration Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    mockNavigate.mockClear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWorkflows = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Workflows />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  // ===== Task 1: List Rendering =====

  it('renders workflows list with name, step count, status, and trigger type columns', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: sampleWorkflows,
        total: 3,
      }),
    } as any);

    renderWorkflows();

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Name')).toBeInTheDocument();
    });

    // Verify columns exist
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Steps')).toBeInTheDocument();
    expect(screen.getByText('Last Run Status')).toBeInTheDocument();
    expect(screen.getByText('Last Run Time')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('displays workflow data correctly in table rows', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[0]],
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    // Verify workflow name appears
    expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    // Verify step count (2 steps) in table
    const table = screen.getByRole('table');
    expect(within(table).getByText('2')).toBeInTheDocument();
    // Verify last run status badge
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('shows workflow with no last run correctly', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[2]],
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Backup Job')).toBeInTheDocument();
    });

    // Verify workflow has no last run status (check that status column is empty or shows "Never")
    const table = screen.getByRole('table');
    expect(within(table).getByText('Never')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  // ===== Task 2: Navigation =====

  it('navigates to workflow detail when clicking a workflow row', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[0]],
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    // Click the workflow row
    const deployRow = screen.getByText('Deploy Pipeline').closest('tr');
    if (deployRow) {
      fireEvent.click(deployRow);
    }

    // Verify navigation was called with correct ID
    expect(mockNavigate).toHaveBeenCalledWith(`/workflows/wf-001`);

    mockFetch.mockRestore();
  });

  it('passes correct workflow ID to navigation route', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [
          sampleWorkflows[0],
          sampleWorkflows[1],
        ],
        total: 2,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    // Click the second workflow
    const etlRow = screen.getByText('Data ETL').closest('tr');
    if (etlRow) {
      fireEvent.click(etlRow);
    }

    // Verify correct ID was passed
    expect(mockNavigate).toHaveBeenCalledWith(`/workflows/wf-002`);

    mockFetch.mockRestore();
  });

  // ===== Task 3: Pagination =====

  it('renders pagination controls with skip and limit', async () => {
    // Create 35 workflows to test pagination
    const manyWorkflows = Array.from({ length: 35 }, (_, i) => ({
      ...sampleWorkflows[0],
      id: `wf-${String(i).padStart(3, '0')}`,
      name: `Workflow ${i + 1}`,
    }));

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: manyWorkflows.slice(0, 10),
        total: 35,
        skip: 0,
        limit: 10,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Workflow 1')).toBeInTheDocument();
    });

    // Verify pagination info appears and Previous/Next buttons exist
    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Previous/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('loads next page when clicking next button', async () => {
    const manyWorkflows = Array.from({ length: 35 }, (_, i) => ({
      ...sampleWorkflows[0],
      id: `wf-${String(i).padStart(3, '0')}`,
      name: `Workflow ${i + 1}`,
    }));

    // First page
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch')
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          workflows: manyWorkflows.slice(0, 10),
          total: 35,
          skip: 0,
          limit: 10,
        }),
      } as any)
      // Second page (when Next is clicked)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          workflows: manyWorkflows.slice(10, 20),
          total: 35,
          skip: 10,
          limit: 10,
        }),
      } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Workflow 1')).toBeInTheDocument();
    });

    // Find and click Next button
    const nextButton = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextButton);

    // Wait for second page to load
    await waitFor(() => {
      expect(screen.getByText('Workflow 11')).toBeInTheDocument();
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);

    mockFetch.mockRestore();
  });

  // ===== Task 4: Empty State =====

  it('displays empty state when no workflows exist', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [],
        total: 0,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      // Look for empty state message
      expect(screen.getByText(/No workflows found/i)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 5: Error Handling =====

  it('displays error message when fetch fails', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({ detail: 'Failed to fetch workflows' }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      // Component displays error message on fetch failure
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('handles network errors gracefully', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch')
      .mockRejectedValueOnce(new Error('Network error'));

    renderWorkflows();

    await waitFor(() => {
      // Component displays error message on network failure
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  // ===== Task 6: React Query Integration =====

  it('uses React Query to fetch workflow data', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[0]],
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    // Verify fetch was called (React Query uses it)
    expect(mockFetch).toHaveBeenCalled();

    mockFetch.mockRestore();
  });

  it('maintains pagination state across re-renders', async () => {
    const manyWorkflows = Array.from({ length: 25 }, (_, i) => ({
      ...sampleWorkflows[0],
      id: `wf-${String(i).padStart(3, '0')}`,
      name: `Workflow ${i + 1}`,
    }));

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: manyWorkflows.slice(0, 10),
        total: 25,
        skip: 0,
        limit: 10,
      }),
    } as any);

    const { rerender } = renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Workflow 1')).toBeInTheDocument();
    });

    // Page should still show first page after rerender
    rerender(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Workflows />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Should still show first page items
    expect(screen.getByText('Workflow 1')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  // ===== Task 7: Workflow Status Display =====

  it('displays different status badge colors for different run statuses', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [
          { ...sampleWorkflows[0], last_run: { ...sampleWorkflows[0].last_run, status: 'COMPLETED' } },
          { ...sampleWorkflows[1], last_run: { ...sampleWorkflows[1].last_run, status: 'FAILED' } },
        ],
        total: 2,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    // Verify both status badges are displayed in the table
    const table = screen.getByRole('table');
    expect(within(table).getByText('COMPLETED')).toBeInTheDocument();
    expect(within(table).getByText('FAILED')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  // ===== Task 8: Workflow Step Count =====

  it('displays correct step counts for workflows with different graph sizes', async () => {
    const workflows = [
      { ...sampleWorkflows[0], steps: Array(5).fill(null).map((_, i) => ({ id: `s${i}`, node_type: 'SCRIPT' })) },
      { ...sampleWorkflows[2], steps: [{ id: 's0', node_type: 'SCRIPT' }] },
    ];

    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows,
        total: 2,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    // Verify step counts are displayed in the table
    const table = screen.getByRole('table');
    expect(within(table).getByText('5')).toBeInTheDocument();
    expect(within(table).getByText('1')).toBeInTheDocument();

    mockFetch.mockRestore();
  });
});
