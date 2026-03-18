import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Nodes from '../Nodes';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

// Mock useWebSocket — Nodes.tsx uses live WebSocket updates
vi.mock('../../hooks/useWebSocket', () => ({
    useWebSocket: vi.fn(),
}));

// Mock sub-modals to avoid rendering complexity
vi.mock('../../components/AddNodeModal', () => ({
    default: () => null,
}));
vi.mock('../../components/ManageMountsModal', () => ({
    default: () => null,
}));
vi.mock('../../components/HotUpgradeModal', () => ({
    default: () => null,
}));

// Mock ResizeObserver (used by recharts ResponsiveContainer)
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};

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

const makeNode = (overrides: Record<string, unknown> = {}) => ({
    node_id: 'node-001',
    hostname: 'test-host',
    ip: '10.0.0.1',
    status: 'ONLINE',
    last_seen: new Date().toISOString(),
    base_os_family: 'DEBIAN',
    stats: { cpu: 10, ram: 20 },
    version: '1.0.0',
    tags: [],
    capabilities: {},
    expected_capabilities: {},
    stats_history: [],
    ...overrides,
});

describe('Nodes View — ENVTAG-03', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    // ── ENVTAG-03: env_tag badge display ───────────────────────────────────

    it('ENVTAG-03: renders a PROD badge for a node with env_tag "PROD"', async () => {
        const nodes = [makeNode({ node_id: 'node-prod', hostname: 'prod-host', env_tag: 'PROD' })];

        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(nodes),
        });

        renderWithProviders(<Nodes />);

        await waitFor(() => {
            expect(screen.getByText('PROD')).toBeInTheDocument();
        });
    });

    it('ENVTAG-03: renders a DEV badge for a node with env_tag "DEV"', async () => {
        const nodes = [makeNode({ node_id: 'node-dev', hostname: 'dev-host', env_tag: 'DEV' })];

        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(nodes),
        });

        renderWithProviders(<Nodes />);

        await waitFor(() => {
            expect(screen.getByText('DEV')).toBeInTheDocument();
        });
    });

    it('ENVTAG-03: renders no env tag badge when env_tag is absent', async () => {
        const nodes = [makeNode({ node_id: 'node-plain', hostname: 'plain-host' })];

        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(nodes),
        });

        renderWithProviders(<Nodes />);

        await waitFor(() => {
            // "UNTAGGED" must never appear — absent env_tag means no badge
            expect(screen.queryByText('UNTAGGED')).not.toBeInTheDocument();
        });
    });

    // ── ENVTAG-03: env filter dropdown ─────────────────────────────────────

    it('ENVTAG-03: an env filter dropdown renders above the node cards', async () => {
        const nodes = [
            makeNode({ node_id: 'node-prod-1', hostname: 'prod-host', env_tag: 'PROD' }),
            makeNode({ node_id: 'node-dev-1', hostname: 'dev-host', env_tag: 'DEV' }),
        ];

        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(nodes),
        });

        renderWithProviders(<Nodes />);

        await waitFor(() => {
            // The env filter should appear — look for "Environment" label or "All Environments" option
            const filterLabel =
                screen.queryByText(/Environment/i) ||
                screen.queryByText(/All Environments/i) ||
                screen.queryByText(/Filter by env/i);
            expect(filterLabel).toBeInTheDocument();
        });
    });

    it('ENVTAG-03: selecting PROD in the env filter shows only PROD-tagged nodes', async () => {
        const nodes = [
            makeNode({ node_id: 'node-prod-2', hostname: 'prod-host', env_tag: 'PROD' }),
            makeNode({ node_id: 'node-dev-2', hostname: 'dev-host', env_tag: 'DEV' }),
        ];

        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(nodes),
        });

        renderWithProviders(<Nodes />);

        await waitFor(() => {
            expect(screen.getByText('prod-host')).toBeInTheDocument();
            expect(screen.getByText('dev-host')).toBeInTheDocument();
        });

        // The env filter is not yet implemented — this assertion intentionally fails RED.
        // After implementation: triggering PROD filter should hide dev-host.
        // For now, verify the filter dropdown exists so the implementation plan has something to wire.
        const filterEl =
            screen.queryByText(/All Environments/i) ||
            screen.queryByText(/Environment/i);
        expect(filterEl).toBeInTheDocument();

        // After selecting PROD, dev-host should disappear.
        // This assertion is RED until the filter logic is built.
        // Placeholder: we check that there is exactly one env filter interaction point.
        // When implemented, userEvent.selectOptions / userEvent.click will be added here.
        //
        // Assert failure to keep the test RED:
        expect(screen.queryByText('dev-host')).not.toBeInTheDocument();
    });
});
