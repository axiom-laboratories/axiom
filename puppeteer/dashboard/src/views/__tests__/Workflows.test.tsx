import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';
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
 * Sample Workflow fixtures for testing
 */
export const sampleWorkflows = [
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

describe('Workflows List View', () => {
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

  const renderWorkflows = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Workflows />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  it('renders list of workflows with columns', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: sampleWorkflows,
        total: 3,
      }),
    } as any);

    renderWorkflows();

    // Wait for async data load with proper RTL pattern
    await waitFor(() => {
      expect(screen.getByText('Name')).toBeInTheDocument();
    });

    expect(screen.getByText('Steps')).toBeInTheDocument();
    expect(screen.getByText('Last Run Status')).toBeInTheDocument();
    expect(screen.getByText('Last Run Time')).toBeInTheDocument();
    expect(screen.getByText('Trigger Type')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('displays workflow data in rows', async () => {
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

    mockFetch.mockRestore();
  });

  it('shows step count for each workflow', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[0], sampleWorkflows[2]],
        total: 2,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      // Deploy Pipeline has 2 steps
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    const counts = screen.getAllByText(/^\d+$/);
    const stepCounts = counts.map((el) => parseInt(el.textContent || '', 10));
    expect(stepCounts).toContain(2);
    expect(stepCounts).toContain(1);

    mockFetch.mockRestore();
  });

  it('displays last run status with correct badge variant', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[0]],
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('shows trigger type (MANUAL/CRON)', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[0], sampleWorkflows[1]],
        total: 2,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Deploy Pipeline')).toBeInTheDocument();
    });

    const cronBadges = screen.getAllByText('CRON');
    expect(cronBadges.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('MANUAL')).toBeInTheDocument();

    mockFetch.mockRestore();
  });

  it('pagination: Previous button disabled on first page', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: sampleWorkflows,
        total: 3,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      // Get buttons by text content with flexible matching
      const buttons = screen.getAllByRole('button');
      const prevButton = buttons.find((btn) => btn.textContent?.includes('Previous'));
      expect(prevButton).toBeDisabled();
    });

    mockFetch.mockRestore();
  });

  it('pagination: Next button disabled on last page', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: sampleWorkflows.slice(0, 1),
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      const buttons = screen.getAllByRole('button');
      const nextButton = buttons.find((btn) => btn.textContent?.includes('Next'));
      expect(nextButton).toBeDisabled();
    });

    mockFetch.mockRestore();
  });

  it('clicking a workflow row navigates to detail page', async () => {
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

    const deployRow = screen.getByText('Deploy Pipeline').closest('tr');
    if (deployRow) {
      fireEvent.click(deployRow);
    }

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/workflows/wf-001');
    });

    mockFetch.mockRestore();
  });

  it('empty state when no workflows exist', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [],
        total: 0,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('No workflows found.')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('displays total count in header', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: sampleWorkflows,
        total: 3,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('3 workflow(s)')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('shows "Never" for workflows with no last run', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        workflows: [sampleWorkflows[2]],
        total: 1,
      }),
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText('Never')).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });

  it('displays error message on fetch failure', async () => {
    const mockFetch = vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: false,
    } as any);

    renderWorkflows();

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });

    mockFetch.mockRestore();
  });
});
