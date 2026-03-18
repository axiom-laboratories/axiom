import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import JobDefinitions from '../JobDefinitions';
import { BrowserRouter } from 'react-router-dom';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

describe('JobDefinitions View', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default mocks for loadData
        mockAuthFetch.mockImplementation((endpoint) => {
            if (endpoint === '/jobs/definitions') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            return Promise.resolve({ ok: false });
        });
    });

    it('renders the page title and description', async () => {
        render(
            <BrowserRouter>
                <JobDefinitions />
            </BrowserRouter>
        );

        // Wait for loading to finish
        await waitFor(() => {
            expect(screen.queryByClassName?.('animate-pulse')).not.toBeInTheDocument();
        }, { timeout: 3000 }).catch(() => { }); // Fallback if pulse check fails

        expect(screen.getByText(/Scheduled Jobs/i)).toBeInTheDocument();
        expect(screen.getByText(/Signed, zero-trust recurring payloads/i)).toBeInTheDocument();
    });

    it('shows the "Archive New Payload" button', async () => {
        render(
            <BrowserRouter>
                <JobDefinitions />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText(/Archive New Payload/i)).toBeInTheDocument();
        });
    });

    // ── OUTPUT-04 / RETRY-03: History panel on definition click (RED) ──────

    it('OUTPUT-04: clicking a job definition name renders a history panel below the list', async () => {
        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/jobs/definitions') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{ id: 'def-abc', name: 'Daily Sync', schedule: '0 * * * *' }]),
                });
            }
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });

        render(
            <BrowserRouter>
                <JobDefinitions />
            </BrowserRouter>
        );

        // Wait for the definition to appear in the list
        await waitFor(() => {
            expect(screen.getByText('Daily Sync')).toBeInTheDocument();
        });

        // Click on the definition name to select it
        fireEvent.click(screen.getByText('Daily Sync'));

        // A history panel must appear below the list.
        // RED until the feature is implemented.
        await waitFor(() => {
            const historyPanel =
                screen.queryByText(/Execution History/i) ||
                screen.queryByText(/Run History/i) ||
                screen.queryByText(/Recent Executions/i);
            expect(historyPanel).toBeInTheDocument();
        });
    });

    it('OUTPUT-04: history panel calls GET /api/executions?scheduled_job_id=X when definition is selected', async () => {
        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/jobs/definitions') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{ id: 'def-xyz', name: 'Nightly Cleanup', schedule: '0 3 * * *' }]),
                });
            }
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (typeof endpoint === 'string' && endpoint.includes('/api/executions')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });

        render(
            <BrowserRouter>
                <JobDefinitions />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Nightly Cleanup')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Nightly Cleanup'));

        // After clicking, the component should call GET /api/executions?scheduled_job_id=def-xyz.
        // RED until the history panel fetch is wired up.
        await waitFor(() => {
            const executionCalls = mockAuthFetch.mock.calls.filter(([url]: [string]) =>
                typeof url === 'string' &&
                url.includes('/api/executions') &&
                url.includes('scheduled_job_id=def-xyz')
            );
            expect(executionCalls.length).toBeGreaterThan(0);
        });
    });
});
