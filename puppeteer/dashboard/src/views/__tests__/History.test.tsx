import { render, screen, waitFor } from '@testing-library/react';
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

    // ── OUTPUT-04: definition selector (RED — not yet implemented) ─────────

    it('OUTPUT-04: a Scheduled Job / Definition selector dropdown appears as a 4th filter', async () => {
        renderWithProviders(<History />);

        await waitFor(() => {
            // The definition selector label or placeholder must be visible.
            // Implementation will add a 4th filter column labelled "Scheduled Job" or "Definition".
            const selector =
                screen.queryByText(/Scheduled Job/i) ||
                screen.queryByText(/Definition/i) ||
                screen.queryByPlaceholderText(/Filter by definition/i);
            expect(selector).toBeInTheDocument();
        });
    });

    it('OUTPUT-04: when a definition is selected the executions query URL includes scheduled_job_id param', async () => {
        renderWithProviders(<History />);

        // Wait for the component to settle
        await waitFor(() => {
            expect(screen.getByText(/Execution History/i)).toBeInTheDocument();
        });

        // Verify that when definition filtering is present, the API call carries the param.
        // This test looks for a call to /api/executions that includes scheduled_job_id.
        // RED until the filter is wired up and triggers the query.
        const executionsCalls = mockAuthFetch.mock.calls.filter(([url]: [string]) =>
            url.includes('/api/executions') && url.includes('scheduled_job_id')
        );

        // After selecting a definition (which this test can't yet do because the UI isn't built),
        // there should be at least one such call. For now this assertion forces RED.
        expect(executionsCalls.length).toBeGreaterThan(0);
    });
});
