import { render, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Queue from '../Queue';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
    getUser: () => ({ username: 'testuser', role: 'admin' }),
}));

// Mock useWebSocket — Queue.tsx uses live WebSocket updates
vi.mock('../../hooks/useWebSocket', () => ({
    useWebSocket: vi.fn(),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

// Mock ResizeObserver (used by recharts)
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};

// Mock scrollIntoView — not implemented in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn();

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

beforeEach(() => {
    mockAuthFetch.mockReset();
    // Default mock returns empty paginated response for all calls
    mockAuthFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, next_cursor: null }),
    });
});

describe('Queue fetch URLs', () => {
    it('fetches jobs without double /api prefix', async () => {
        renderWithProviders(<Queue />);

        await waitFor(() => {
            expect(mockAuthFetch).toHaveBeenCalled();
        });

        // At least one call should start with /jobs (not /api/jobs)
        const calls = mockAuthFetch.mock.calls.map((c: any[]) => c[0] as string);
        const jobsCalls = calls.filter((url) => url.includes('jobs'));
        expect(jobsCalls.length).toBeGreaterThan(0);

        // None of the calls should start with /api/
        const apiPrefixedCalls = calls.filter((url) => /^\/api\//.test(url));
        expect(apiPrefixedCalls).toHaveLength(0);

        // The jobs fetch should start with /jobs
        const correctJobsCalls = calls.filter((url) => /^\/jobs/.test(url));
        expect(correctJobsCalls.length).toBeGreaterThan(0);
    });

    it('fetches nodes without double /api prefix', async () => {
        renderWithProviders(<Queue />);

        await waitFor(() => {
            expect(mockAuthFetch).toHaveBeenCalled();
        });

        const calls = mockAuthFetch.mock.calls.map((c: any[]) => c[0] as string);

        // The nodes fetch should not use /api/nodes
        const apiNodesCalls = calls.filter((url) => url === '/api/nodes');
        expect(apiNodesCalls).toHaveLength(0);

        // The nodes fetch should use /nodes
        const nodesCalls = calls.filter((url) => url === '/nodes');
        expect(nodesCalls.length).toBeGreaterThan(0);
    });
});
