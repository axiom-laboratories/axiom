import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import History from '../History';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

// Mock ExecutionLogModal to avoid nested fetch complexity
vi.mock('../../components/ExecutionLogModal', () => ({
    ExecutionLogModal: () => null,
}));

const createQueryClient = () =>
    new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });

const renderWithProviders = (ui: React.ReactElement) =>
    render(
        <BrowserRouter>
            <QueryClientProvider client={createQueryClient()}>
                {ui}
            </QueryClientProvider>
        </BrowserRouter>
    );

describe('History View', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        mockAuthFetch.mockImplementation((url: string) => {
            if (url.includes('/api/executions')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            if (url.includes('/jobs/definitions')) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve([{ id: 'def-1', name: 'My Job' }]),
                });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });
    });

    // ── OUTPUT-04 regression guards ────────────────────────────────────────

    it('OUTPUT-04: renders the Job GUID filter input (regression guard)', async () => {
        renderWithProviders(<History />);

        await waitFor(() => {
            // getAllByText handles multiple elements with same text
            const els = screen.getAllByText(/Job GUID/i);
            expect(els.length).toBeGreaterThan(0);
        });
    });

    it('OUTPUT-04: renders the Node ID filter input (regression guard)', async () => {
        renderWithProviders(<History />);

        await waitFor(() => {
            const els = screen.getAllByText(/Node ID/i);
            expect(els.length).toBeGreaterThan(0);
        });
    });

    it('OUTPUT-04: renders the Status filter dropdown (regression guard)', async () => {
        renderWithProviders(<History />);

        await waitFor(() => {
            const els = screen.getAllByText(/Status/i);
            expect(els.length).toBeGreaterThan(0);
        });
    });

    // ── OUTPUT-04: definition selector ────────────────────────────────────

    it('OUTPUT-04: a Scheduled Job / Definition selector dropdown appears as a 4th filter', async () => {
        renderWithProviders(<History />);

        await waitFor(() => {
            // The definition selector label or placeholder must be visible.
            const selector =
                screen.queryByText(/Scheduled Job/i) ||
                screen.queryByText(/Definition/i) ||
                screen.queryByPlaceholderText(/Filter by definition/i);
            expect(selector).toBeInTheDocument();
        });
    });

    it('OUTPUT-04: History fetches /jobs/definitions to populate definition selector', async () => {
        renderWithProviders(<History />);

        await waitFor(() => {
            const defCalls = mockAuthFetch.mock.calls.filter(([url]: [string]) =>
                url.includes('/jobs/definitions')
            );
            expect(defCalls.length).toBeGreaterThan(0);
        });
    });

    // ── VALD-03: failure_reason in execution history ─────────────────────────

    it('VALD-03: execution history shows failure_reason for validation failures', async () => {
        mockAuthFetch.mockImplementation((url: string) => {
            if (url.includes('/api/executions') || (url.includes('/executions') && !url.includes('/jobs/definitions'))) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{
                        id: 999,
                        job_guid: 'guid-abc',
                        node_id: 'node-1',
                        status: 'FAILED',
                        failure_reason: 'validation_regex',
                        started_at: new Date().toISOString(),
                        duration_seconds: 0.8,
                    }]),
                });
            }
            if (url.includes('/jobs/definitions')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{ id: 'def-1', name: 'My Job' }]),
                });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });

        renderWithProviders(<History />);

        await waitFor(() => {
            expect(screen.getByText(/Validation failed: regex/i)).toBeInTheDocument();
        });
    });
});
