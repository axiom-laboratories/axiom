import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import JobDefinitions from '../JobDefinitions';
import JobDefinitionModal from '../../components/job-definitions/JobDefinitionModal';
import { BrowserRouter } from 'react-router-dom';

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
    new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderWithProviders = (ui: React.ReactElement) =>
    render(
        <BrowserRouter>
            <QueryClientProvider client={createQueryClient()}>
                {ui}
            </QueryClientProvider>
        </BrowserRouter>
    );

describe('JobDefinitions View', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default mocks for loadData
        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/jobs/definitions') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (typeof endpoint === 'string' && endpoint.includes('/api/executions')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            return Promise.resolve({ ok: false });
        });
    });

    it('renders the page title and description', async () => {
        renderWithProviders(<JobDefinitions />);

        // Wait for loading to finish
        await waitFor(() => {
            expect(screen.queryByClassName?.('animate-pulse')).not.toBeInTheDocument();
        }, { timeout: 3000 }).catch(() => { }); // Fallback if pulse check fails

        expect(screen.getByText(/Scheduled Jobs/i)).toBeInTheDocument();
        expect(screen.getByText(/Signed, zero-trust recurring payloads/i)).toBeInTheDocument();
    });

    it('shows the "Archive New Payload" button', async () => {
        renderWithProviders(<JobDefinitions />);

        await waitFor(() => {
            expect(screen.getByText(/Archive New Payload/i)).toBeInTheDocument();
        });
    });

    // ── OUTPUT-04 / RETRY-03: History panel on definition click ──────

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
            if (typeof endpoint === 'string' && endpoint.includes('/api/executions')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });

        renderWithProviders(<JobDefinitions />);

        // Wait for the definition to appear in the list
        await waitFor(() => {
            expect(screen.getByText('Daily Sync')).toBeInTheDocument();
        });

        // Click on the definition name to select it
        fireEvent.click(screen.getByText('Daily Sync'));

        // A history panel must appear below the list.
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

        renderWithProviders(<JobDefinitions />);

        await waitFor(() => {
            expect(screen.getByText('Nightly Cleanup')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Nightly Cleanup'));

        // After clicking, the component should call GET /api/executions?scheduled_job_id=def-xyz.
        await waitFor(() => {
            const executionCalls = mockAuthFetch.mock.calls.filter(([url]: [string]) =>
                typeof url === 'string' &&
                url.includes('/api/executions') &&
                url.includes('scheduled_job_id=def-xyz')
            );
            expect(executionCalls.length).toBeGreaterThan(0);
        });
    });

    // ── VALD-01: Validation Rules form section ──────────────────────────────

    it('VALD-01: job definition modal renders Validation Rules section', async () => {
        const emptyFormData = {
            name: '',
            script_content: '',
            signature: '',
            signature_id: '',
            schedule_cron: '* * * * *',
            target_node_id: '',
            target_tags: '',
            capability_requirements: '',
            allow_overlap: false,
            dispatch_timeout_minutes: null,
            validation_exit_code: '0',
            validation_stdout_regex: '',
            validation_json_path: '',
            validation_json_expected: '',
        };
        render(
            <BrowserRouter>
                <JobDefinitionModal
                    isOpen={true}
                    onClose={() => {}}
                    onSubmit={(e) => e.preventDefault()}
                    formData={emptyFormData}
                    setFormData={() => {}}
                    signatures={[]}
                    editingJob={null}
                />
            </BrowserRouter>
        );
        await waitFor(() => {
            expect(screen.getByText(/Validation Rules/i)).toBeInTheDocument();
        });
    });

    it('VALD-01: validation section auto-expands when editing job with rules', async () => {
        const formData = {
            name: 'Test Job',
            script_content: 'print("hello")',
            signature: 'sig',
            signature_id: 'key-1',
            schedule_cron: '* * * * *',
            target_node_id: '',
            target_tags: '',
            capability_requirements: '',
            allow_overlap: false,
            dispatch_timeout_minutes: null,
            validation_exit_code: '0',
            validation_stdout_regex: 'OK',
            validation_json_path: '',
            validation_json_expected: '',
        };
        const editingJob = {
            id: 'def-1',
            name: 'Test Job',
            script_content: 'print("hello")',
            signature_id: 'key-1',
            signature_payload: 'sig',
            schedule_cron: '* * * * *',
            target_node_id: null,
            target_tags: null,
            capability_requirements: null,
            allow_overlap: false,
            dispatch_timeout_minutes: null,
            validation_rules: { exit_code: 0, stdout_regex: 'OK' },
        };
        render(
            <BrowserRouter>
                <JobDefinitionModal
                    isOpen={true}
                    onClose={() => {}}
                    onSubmit={(e) => e.preventDefault()}
                    formData={formData}
                    setFormData={() => {}}
                    signatures={[]}
                    editingJob={editingJob}
                />
            </BrowserRouter>
        );
        // Wait for section to auto-expand (useEffect fires with editingJob)
        await waitFor(() => {
            // The expanded section shows the exit code input label
            expect(screen.getByText(/Expected exit code/i)).toBeInTheDocument();
        });
    });

    // ── VALD-03: DefinitionHistoryPanel failure_reason display ──────────────

    it('VALD-03: DefinitionHistoryPanel shows validation failure label for validation failures', async () => {
        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/jobs/definitions') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{ id: 'def-v', name: 'Validated Job', schedule: '0 * * * *', status: 'ACTIVE' }]),
                });
            }
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (typeof endpoint === 'string' && endpoint.includes('/executions') && endpoint.includes('scheduled_job_id=def-v')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{
                        id: 100,
                        status: 'FAILED',
                        failure_reason: 'validation_exit_code',
                        node_id: 'node-1',
                        started_at: new Date().toISOString(),
                        duration_seconds: 1.2,
                        attempt_number: 1,
                        max_retries: 0,
                        job_run_id: null,
                    }]),
                });
            }
            if (typeof endpoint === 'string' && endpoint.includes('/jobs/definitions/def-v/versions')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });

        renderWithProviders(<JobDefinitions />);

        await waitFor(() => {
            expect(screen.getByText('Validated Job')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Validated Job'));

        await waitFor(() => {
            expect(screen.getByText(/Validation failed: exit_code/i)).toBeInTheDocument();
        });
    });

    it('VALD-03: DefinitionHistoryPanel does not show validation label for runtime failures', async () => {
        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/jobs/definitions') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{ id: 'def-r', name: 'Runtime Job', schedule: '0 * * * *', status: 'ACTIVE' }]),
                });
            }
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (typeof endpoint === 'string' && endpoint.includes('/executions') && endpoint.includes('scheduled_job_id=def-r')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([{
                        id: 200,
                        status: 'FAILED',
                        failure_reason: null,
                        node_id: 'node-2',
                        started_at: new Date().toISOString(),
                        duration_seconds: 0.5,
                        attempt_number: 1,
                        max_retries: 0,
                        job_run_id: null,
                    }]),
                });
            }
            if (typeof endpoint === 'string' && endpoint.includes('/jobs/definitions/def-r/versions')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            return Promise.resolve({ ok: false, json: () => Promise.resolve([]) });
        });

        renderWithProviders(<JobDefinitions />);

        await waitFor(() => {
            expect(screen.getByText('Runtime Job')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Runtime Job'));

        await waitFor(() => {
            // Status badge for FAILED row should exist
            expect(screen.getByText('FAILED')).toBeInTheDocument();
        });

        // No validation failure label
        expect(screen.queryByText(/Validation failed/i)).not.toBeInTheDocument();
    });
});
