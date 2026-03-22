import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Templates from '../Templates';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

// Mock useFeatures — enable foundry so the real UI renders (not the UpgradePlaceholder)
vi.mock('../../hooks/useFeatures', () => ({
    useFeatures: () => ({
        foundry: true,
        audit: false,
        webhooks: false,
        triggers: false,
        rbac: false,
        resource_limits: false,
        service_principals: false,
        api_keys: false,
    }),
}));

// Mock heavy child dialogs to avoid rendering complexity
vi.mock('../../components/CreateTemplateDialog', () => ({
    CreateTemplateDialog: () => null,
}));
vi.mock('../../components/foundry/BlueprintWizard', () => ({
    default: () => null,
}));

// Mock ResizeObserver (used by recharts/Radix internals)
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};

// Prevent Radix Select crash in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn();

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

// ── Minimal API response shapes ──────────────────────────────────────────────

const mockBlueprint = {
    id: 'bp-001',
    name: 'Test Runtime',
    type: 'RUNTIME',
    version: 1,
    os_family: 'DEBIAN',
    definition: JSON.stringify({ base_os: 'debian:12-slim', packages: { python: [] }, tools: [] }),
    created_at: new Date().toISOString(),
};

const mockTemplate = {
    id: 'tpl-001',
    friendly_name: 'Test Template',
    canonical_id: 'abc123',
    last_built_image: null,
    last_built_at: null,
    runtime_blueprint_id: 'bp-001',
    network_blueprint_id: null,
    created_at: new Date().toISOString(),
};

const mockTool = {
    id: 'tool-001',
    tool_id: 'python3',
    base_os_family: 'DEBIAN',
    validation_cmd: 'python3 --version',
    injection_recipe: 'apt-get install -y python3',
    runtime_dependencies: [],
    is_active: true,
};

// ── BRAND-01 smoke tests ──────────────────────────────────────────────────────

describe('BRAND-01: Foundry UI label rename', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/api/templates') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([mockTemplate]) });
            }
            if (endpoint === '/api/blueprints') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([mockBlueprint]) });
            }
            if (endpoint === '/admin/base-image-updated') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve({ base_node_image_updated_at: null }) });
            }
            if (endpoint === '/api/capability-matrix') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([mockTool]) });
            }
            if (endpoint === '/api/approved-os') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            if (endpoint === '/api/smelter/ingredients') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
        });
    });

    it('BRAND-01a: tab labels contain "Image Recipe" not "Blueprint"', async () => {
        renderWithProviders(<Templates />);

        await waitFor(() => {
            // At least one tab with "Image Recipe" must be rendered
            const runtimeTab = screen.queryByText(/Runtime Image Recipe/i);
            const networkTab = screen.queryByText(/Network Image Recipe/i);
            expect(runtimeTab || networkTab).not.toBeNull();
        }, { timeout: 5000 });
    });

    it('BRAND-01b: "Node Image" appears somewhere in the Foundry tabs', async () => {
        renderWithProviders(<Templates />);

        await waitFor(() => {
            // "Node Image" label appears in at least one place (tab, button, or empty state)
            // After rename: "Compose Node Image" in tab or button context
            const nodeImageEl = screen.queryByText(/Node Image/i);
            expect(nodeImageEl).not.toBeNull();
        }, { timeout: 5000 });
    });

    it('BRAND-01c: legacy label "Blueprint" (standalone) is not visible in the Foundry tab list', async () => {
        renderWithProviders(<Templates />);

        await waitFor(() => {
            // The tab list renders after data loads — wait for the "Templates" tab
            expect(screen.queryByText(/Templates \(\d+\)/i)).toBeInTheDocument();
        }, { timeout: 5000 });

        // Standalone "Blueprint" tab label must not appear
        // "Runtime Blueprints" / "Network Blueprints" — these are the strings to eliminate
        expect(screen.queryByText(/Runtime Blueprints/i)).toBeNull();
        expect(screen.queryByText(/Network Blueprints/i)).toBeNull();
    });

    it('BRAND-01d: "Puppet Template" does not appear anywhere in the rendered output', async () => {
        const { container } = renderWithProviders(<Templates />);

        await waitFor(() => {
            expect(screen.queryByText(/Templates \(\d+\)/i)).toBeInTheDocument();
        }, { timeout: 5000 });

        expect(container.textContent).not.toMatch(/Puppet Template/i);
    });

    it('BRAND-01e: "Capability Matrix" does not appear in the Foundry tabs', async () => {
        const { container } = renderWithProviders(<Templates />);

        await waitFor(() => {
            expect(screen.queryByText(/Templates \(\d+\)/i)).toBeInTheDocument();
        }, { timeout: 5000 });

        expect(container.textContent).not.toMatch(/Capability Matrix/i);
    });
});
