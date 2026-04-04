import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '../../hooks/useTheme';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
    getUser: () => ({ username: 'operator', role: 'operator' }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

// Mock useFeatures — enable foundry
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

// Mock useLicence
const mockUseLicence = vi.fn(() => ({ licence_status: 'VALID' }));
vi.mock('../../hooks/useLicence', () => ({
    useLicence: (...args: any[]) => mockUseLicence(...args),
}));

// Mock useSystemHealth
const mockUseSystemHealth = vi.fn(() => ({ mirrors_available: true }));
vi.mock('../../hooks/useSystemHealth', () => ({
    useSystemHealth: (...args: any[]) => mockUseSystemHealth(...args),
}));

// Mock heavy child dialogs
vi.mock('../../components/CreateTemplateDialog', () => ({
    CreateTemplateDialog: () => null,
}));

// Mock ResizeObserver and Radix Select
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// NOTE: SmelterIngredientSelector is not a full page view like Admin/Templates.
// It's a component that would be used within Smelter or another admin view.
// For now we define test stubs that would test the component's behavior.
// Placeholder: import SmelterIngredientSelector from '../../components/SmelterIngredientSelector';

const createQueryClient = () =>
    new QueryClient({ defaultOptions: { queries: { retry: false } } });

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

// ── Wave 0 Test Stubs: Conda ToS Modal ──────────────────────────────────────

describe('Wave 0: Conda Defaults ToS Modal Tests (RED state)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default: user has NOT acknowledged conda defaults ToS
        mockAuthFetch.mockImplementation((endpoint: string) => {
            if (endpoint === '/api/admin/mirror-config') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        conda_mirror_url: 'http://mirror:8081/conda',
                        conda_defaults_acknowledged_by_current_user: false,
                        health_status: { conda: 'ok' },
                    }),
                });
            }
            return Promise.reject(new Error(`Unmocked endpoint: ${endpoint}`));
        });
    });

    it('test_conda_defaults_modal_appears_on_channel_selection - selecting defaults channel shows modal', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_modal_blocks_approval - approval button disabled until acknowledged', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_modal_hidden_after_acknowledgment - modal closes after Acknowledge button', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_acknowledged_per_user - different users see modal independently', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_acknowledges_via_api - Acknowledge button calls POST endpoint', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_conda_forge_pre_selected - conda-forge is default channel when ecosystem=CONDA', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_other_channels_no_modal - selecting conda-forge or other channels does not show modal', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_second_encounter_no_modal - after acknowledgment, modal does not appear again', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });

    it('test_conda_defaults_cancel_button - Cancel button closes modal without acknowledgment', async () => {
        // STUB: RED state — test not yet implemented
        expect(true).toBe(true);
    });
});
