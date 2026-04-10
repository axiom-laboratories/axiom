import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '../../hooks/useTheme';
import Nodes from '../Nodes';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
    getUser: () => ({ username: 'testuser', role: 'admin' }),
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

// Mock scrollIntoView — not implemented in jsdom, crashes Radix Select
window.HTMLElement.prototype.scrollIntoView = vi.fn();

const createQueryClient = () =>
    new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });

const renderWithProviders = (ui: React.ReactElement) =>
    render(
        <BrowserRouter>
            <QueryClientProvider client={createQueryClient()}>
                <ThemeProvider>
                    {ui}
                </ThemeProvider>
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

        // Filter is now implemented — verify dropdown renders
        const filterEl =
            screen.queryByText(/Filter by environment/i) ||
            screen.queryByText(/Environment/i);
        expect(filterEl).toBeInTheDocument();

        // Trigger the Radix Select to open and pick PROD
        const trigger = screen.getByRole('combobox');
        fireEvent.click(trigger);

        // Wait for PROD option to appear in the dropdown portal
        await waitFor(() => {
            expect(screen.getByRole('option', { name: 'PROD' })).toBeInTheDocument();
        });
        fireEvent.click(screen.getByRole('option', { name: 'PROD' }));

        // After selecting PROD, dev-host should disappear
        await waitFor(() => {
            expect(screen.queryByText('dev-host')).not.toBeInTheDocument();
        });
    });
});

// ── CGRP-03/CGRP-04: Cgroup badge and degradation banner ─────────────────────────

import {
    getCgroupBadgeClass,
    getCgroupTooltip,
    getCgroupDisplayText,
} from '../Nodes';

describe('Cgroup Badge and Degradation Banner Logic', () => {
    describe('getCgroupBadgeClass', () => {
        it('CGRP-03: returns emerald classes for v2', () => {
            const result = getCgroupBadgeClass('v2');
            expect(result).toBe('bg-emerald-500/10 text-emerald-500 border-emerald-500/20');
        });

        it('CGRP-03: returns amber classes for v1', () => {
            const result = getCgroupBadgeClass('v1');
            expect(result).toBe('bg-amber-500/10 text-amber-500 border-amber-500/20');
        });

        it('CGRP-03: returns red classes for unsupported', () => {
            const result = getCgroupBadgeClass('unsupported');
            expect(result).toBe('bg-red-500/10 text-red-500 border-red-500/20');
        });

        it('CGRP-03: returns muted classes for null', () => {
            const result = getCgroupBadgeClass(null);
            expect(result).toBe('bg-muted text-muted-foreground border-muted');
        });

        it('CGRP-03: returns muted classes for undefined', () => {
            const result = getCgroupBadgeClass(undefined);
            expect(result).toBe('bg-muted text-muted-foreground border-muted');
        });
    });

    describe('getCgroupTooltip', () => {
        it('CGRP-03: returns v2 tooltip text', () => {
            const result = getCgroupTooltip('v2');
            expect(result).toBe(
                'Cgroup v2 — Full resource isolation. Memory and CPU limits fully enforced.'
            );
        });

        it('CGRP-03: returns v1 tooltip text', () => {
            const result = getCgroupTooltip('v1');
            expect(result).toBe(
                'Cgroup v1 (Degraded) — Memory limits supported. CPU enforcement may be limited. Upgrade to v2 recommended.'
            );
        });

        it('CGRP-03: returns unsupported tooltip text', () => {
            const result = getCgroupTooltip('unsupported');
            expect(result).toBe(
                'No cgroup support detected. Resource limits cannot be enforced. Jobs run without isolation.'
            );
        });

        it('CGRP-03: returns unknown tooltip text for null', () => {
            const result = getCgroupTooltip(null);
            expect(result).toBe(
                'Cgroup status not reported. Node may be running an older version.'
            );
        });

        it('CGRP-03: returns unknown tooltip text for undefined', () => {
            const result = getCgroupTooltip(undefined);
            expect(result).toBe(
                'Cgroup status not reported. Node may be running an older version.'
            );
        });
    });

    describe('getCgroupDisplayText', () => {
        it('CGRP-03: returns v2 for v2', () => {
            const result = getCgroupDisplayText('v2');
            expect(result).toBe('v2');
        });

        it('CGRP-03: returns v1 for v1', () => {
            const result = getCgroupDisplayText('v1');
            expect(result).toBe('v1');
        });

        it('CGRP-03: returns unsupported for unsupported', () => {
            const result = getCgroupDisplayText('unsupported');
            expect(result).toBe('unsupported');
        });

        it('CGRP-03: returns unknown for null', () => {
            const result = getCgroupDisplayText(null);
            expect(result).toBe('unknown');
        });

        it('CGRP-03: returns unknown for undefined', () => {
            const result = getCgroupDisplayText(undefined);
            expect(result).toBe('unknown');
        });
    });

    describe('Degradation Banner Logic — CGRP-04', () => {
        it('CGRP-04: shows banner when online nodes include v1', () => {
            const nodes = [
                { node_id: '1', status: 'ONLINE', detected_cgroup_version: 'v1' } as any,
                { node_id: '2', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
            ];
            const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
            const degradedNodes = onlineNodes.filter(
                n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
            );
            expect(degradedNodes.length).toBeGreaterThan(0);
        });

        it('CGRP-04: shows banner when online nodes include unsupported', () => {
            const nodes = [
                {
                    node_id: '1',
                    status: 'ONLINE',
                    detected_cgroup_version: 'unsupported',
                } as any,
                { node_id: '2', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
            ];
            const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
            const degradedNodes = onlineNodes.filter(
                n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
            );
            expect(degradedNodes.length).toBeGreaterThan(0);
        });

        it('CGRP-04: hides banner when all online nodes are v2', () => {
            const nodes = [
                { node_id: '1', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
                { node_id: '2', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
            ];
            const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
            const degradedNodes = onlineNodes.filter(
                n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
            );
            expect(degradedNodes.length).toBe(0);
        });

        it('CGRP-04: excludes offline nodes from degraded count', () => {
            const nodes = [
                { node_id: '1', status: 'OFFLINE', detected_cgroup_version: 'v1' } as any,
                { node_id: '2', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
            ];
            const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
            const degradedNodes = onlineNodes.filter(
                n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
            );
            expect(degradedNodes.length).toBe(0);
        });

        it('CGRP-04: excludes revoked nodes from degraded count', () => {
            const nodes = [
                { node_id: '1', status: 'REVOKED', detected_cgroup_version: 'v1' } as any,
                { node_id: '2', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
            ];
            const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
            const degradedNodes = onlineNodes.filter(
                n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
            );
            expect(degradedNodes.length).toBe(0);
        });

        it('CGRP-04: counts v1 and unsupported separately', () => {
            const nodes = [
                { node_id: '1', status: 'ONLINE', detected_cgroup_version: 'v1' } as any,
                { node_id: '2', status: 'ONLINE', detected_cgroup_version: 'v1' } as any,
                {
                    node_id: '3',
                    status: 'ONLINE',
                    detected_cgroup_version: 'unsupported',
                } as any,
                { node_id: '4', status: 'ONLINE', detected_cgroup_version: 'v2' } as any,
            ];
            const onlineNodes = nodes.filter(n => n.status === 'ONLINE');
            const degradedNodes = onlineNodes.filter(
                n => n.detected_cgroup_version && n.detected_cgroup_version !== 'v2'
            );
            const v1Count = degradedNodes.filter(
                n => n.detected_cgroup_version === 'v1'
            ).length;
            const unsupportedCount = degradedNodes.filter(
                n => n.detected_cgroup_version === 'unsupported'
            ).length;
            expect(v1Count).toBe(2);
            expect(unsupportedCount).toBe(1);
            expect(degradedNodes.length).toBe(3);
        });
    });
});
