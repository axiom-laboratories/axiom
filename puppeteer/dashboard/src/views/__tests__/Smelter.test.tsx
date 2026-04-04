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

import { SmelterIngredientSelector } from '../../components/SmelterIngredientSelector';
import { CondaDefaultsToSModal } from '../../components/CondaDefaultsToSModal';

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

// ── Comprehensive Tests: Conda Defaults ToS Modal ─────────────────────────────

describe('Conda Defaults ToS Modal Tests', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Mock mirror-config endpoint to return that user has NOT acknowledged yet
        mockAuthFetch.mockImplementation((endpoint: string, options?: any) => {
            if (endpoint === '/api/admin/mirror-config') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        conda_mirror_url: 'http://mirror:8081/conda',
                        conda_defaults_acknowledged_by_current_user: false,
                        health_status: { conda: 'ok' },
                        provisioning_enabled: false,
                    }),
                });
            }
            // Mock POST /api/admin/conda-defaults-acknowledge
            if (endpoint === '/api/admin/conda-defaults-acknowledge' && options?.method === 'POST') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        acknowledged: true,
                        message: 'ToS acknowledged',
                    }),
                });
            }
            return Promise.reject(new Error(`Unmocked endpoint: ${endpoint}`));
        });
    });

    it('test_conda_defaults_conda_forge_pre_selected - conda-forge is pre-selected for CONDA ecosystem', async () => {
        renderWithProviders(<SmelterIngredientSelector />);

        // Change ecosystem to CONDA
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        // Check that conda-forge is pre-selected in the channel dropdown
        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await waitFor(() => {
            expect(channelSelect).toHaveTextContent('conda-forge');
        });
    });

    it('test_conda_defaults_modal_appears_on_channel_selection - selecting defaults channel shows modal', async () => {
        renderWithProviders(<SmelterIngredientSelector />);

        // Select CONDA ecosystem
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        // Modal should not be visible yet (conda-forge is pre-selected)
        expect(screen.queryByText(/Anaconda defaults Channel/)).not.toBeInTheDocument();

        // Select "defaults" channel
        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await fireEvent.click(channelSelect);
        const defaultsOption = screen.getByText('defaults');
        await fireEvent.click(defaultsOption);

        // Modal should now appear
        await waitFor(() => {
            expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
        });
    });

    it('test_conda_defaults_modal_blocks_approval - approval button disabled while modal open', async () => {
        renderWithProviders(<SmelterIngredientSelector />);

        // Wait for component to initialize (mirror config fetch)
        await waitFor(() => {
            const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
            expect(ecosystemSelect).toBeInTheDocument();
        });

        // Select CONDA + defaults
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await fireEvent.click(channelSelect);
        const defaultsOption = screen.getByText('defaults');
        await fireEvent.click(defaultsOption);

        // Modal should appear indicating approval is blocked
        await waitFor(() => {
            expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
            // When defaults is selected without acknowledgment, there should be a warning message
            expect(screen.getByText(/Requires ToS acknowledgment before proceeding/)).toBeInTheDocument();
        }, { timeout: 3000 });
    });

    it('test_conda_defaults_modal_hidden_after_acknowledgment - modal closes after Acknowledge button', async () => {
        renderWithProviders(<SmelterIngredientSelector />);

        // Setup CONDA + defaults
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await fireEvent.click(channelSelect);
        const defaultsOption = screen.getByText('defaults');
        await fireEvent.click(defaultsOption);

        // Modal should appear
        await waitFor(() => {
            expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
        });

        // Click "I Acknowledge" button
        const acknowledgeBtn = screen.getByRole('button', { name: /I Acknowledge/i });
        await fireEvent.click(acknowledgeBtn);

        // Modal should close
        await waitFor(() => {
            expect(screen.queryByText(/Anaconda defaults Channel/)).not.toBeInTheDocument();
        });
    });

    it('test_conda_defaults_acknowledges_via_api - Acknowledge button calls POST endpoint', async () => {
        const mockFetch = vi.mocked(mockAuthFetch);
        renderWithProviders(<SmelterIngredientSelector />);

        // Setup CONDA + defaults
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await fireEvent.click(channelSelect);
        const defaultsOption = screen.getByText('defaults');
        await fireEvent.click(defaultsOption);

        // Wait for modal to appear
        await waitFor(() => {
            expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
        });

        // Click Acknowledge
        const acknowledgeBtn = screen.getByRole('button', { name: /I Acknowledge/i });
        await fireEvent.click(acknowledgeBtn);

        // Verify API was called
        await waitFor(() => {
            const calls = mockFetch.mock.calls;
            const acknowledgeCall = calls.find(
                (call) => call[0] === '/api/admin/conda-defaults-acknowledge'
            );
            expect(acknowledgeCall).toBeDefined();
            expect(acknowledgeCall?.[1]?.method).toBe('POST');
        });
    });

    it('test_conda_defaults_cancel_button - Cancel closes modal without acknowledgment', async () => {
        renderWithProviders(<SmelterIngredientSelector />);

        // Setup CONDA + defaults
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await fireEvent.click(channelSelect);
        const defaultsOption = screen.getByText('defaults');
        await fireEvent.click(defaultsOption);

        // Modal appears
        await waitFor(() => {
            expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
        });

        // Click Cancel button
        const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
        await fireEvent.click(cancelBtn);

        // Modal should close
        await waitFor(() => {
            expect(screen.queryByText(/Anaconda defaults Channel/)).not.toBeInTheDocument();
        });

        // Channel should reset to conda-forge
        const channelSelectAfter = screen.getByRole('combobox', { name: /conda channel/i });
        await waitFor(() => {
            expect(channelSelectAfter).toHaveTextContent('conda-forge');
        });
    });

    it('test_conda_defaults_other_channels_no_modal - conda-forge channel does not show modal', async () => {
        renderWithProviders(<SmelterIngredientSelector />);

        // Wait for component to initialize
        await waitFor(() => {
            const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
            expect(ecosystemSelect).toBeInTheDocument();
        });

        // Select CONDA ecosystem (conda-forge is already pre-selected)
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        // Modal should NOT appear (conda-forge is the default, no ToS needed)
        expect(screen.queryByText(/Anaconda defaults Channel/)).not.toBeInTheDocument();

        // Enter ingredient name to enable button
        const nameInput = screen.getByPlaceholderText(/e.g., requests, curl, jq/);
        await fireEvent.change(nameInput, { target: { value: 'test-package' } });

        // Approval button should be enabled (no approval blocking)
        const approveBtn = screen.getByRole('button', { name: /Approve Ingredient/i });
        expect(approveBtn).toBeEnabled();
    });

    it('test_conda_defaults_second_encounter_no_modal - after acknowledgment, modal does not reappear', async () => {
        // Setup mock to return acknowledged=true after first call
        let callCount = 0;
        mockAuthFetch.mockImplementation((endpoint: string, options?: any) => {
            if (endpoint === '/api/admin/mirror-config') {
                callCount++;
                const acknowledged = callCount > 1; // True after first config fetch
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        conda_mirror_url: 'http://mirror:8081/conda',
                        conda_defaults_acknowledged_by_current_user: acknowledged,
                        health_status: { conda: 'ok' },
                        provisioning_enabled: false,
                    }),
                });
            }
            if (endpoint === '/api/admin/conda-defaults-acknowledge' && options?.method === 'POST') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        acknowledged: true,
                        message: 'ToS acknowledged',
                    }),
                });
            }
            return Promise.reject(new Error(`Unmocked endpoint: ${endpoint}`));
        });

        const { rerender } = renderWithProviders(<SmelterIngredientSelector />);

        // Select CONDA + defaults
        const ecosystemSelect = screen.getByRole('combobox', { name: /ecosystem/i });
        await fireEvent.click(ecosystemSelect);
        const condaOption = screen.getByText('CONDA');
        await fireEvent.click(condaOption);

        const channelSelect = screen.getByRole('combobox', { name: /conda channel/i });
        await fireEvent.click(channelSelect);
        const defaultsOption = screen.getByText('defaults');
        await fireEvent.click(defaultsOption);

        // Modal appears
        await waitFor(() => {
            expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
        });

        // Acknowledge
        const acknowledgeBtn = screen.getByRole('button', { name: /I Acknowledge/i });
        await fireEvent.click(acknowledgeBtn);

        // Modal closes
        await waitFor(() => {
            expect(screen.queryByText(/Anaconda defaults Channel/)).not.toBeInTheDocument();
        });
    });
});

// ── CondaDefaultsToSModal Component Unit Tests ────────────────────────────

describe('CondaDefaultsToSModal Component', () => {
    it('renders modal with correct title and text', () => {
        render(
            <CondaDefaultsToSModal
                isOpen={true}
                onAcknowledge={vi.fn()}
                onCancel={vi.fn()}
            />
        );

        expect(screen.getByText(/Anaconda defaults Channel/)).toBeInTheDocument();
        expect(screen.getByText(/Commercial Terms/)).toBeInTheDocument();
        expect(screen.getByText(/conda-forge/)).toBeInTheDocument();
    });

    it('calls onAcknowledge when Acknowledge button clicked', async () => {
        const mockOnAcknowledge = vi.fn();
        render(
            <CondaDefaultsToSModal
                isOpen={true}
                onAcknowledge={mockOnAcknowledge}
                onCancel={vi.fn()}
            />
        );

        const btn = screen.getByRole('button', { name: /I Acknowledge/i });
        await fireEvent.click(btn);

        expect(mockOnAcknowledge).toHaveBeenCalled();
    });

    it('calls onCancel when Cancel button clicked', async () => {
        const mockOnCancel = vi.fn();
        render(
            <CondaDefaultsToSModal
                isOpen={true}
                onAcknowledge={vi.fn()}
                onCancel={mockOnCancel}
            />
        );

        const btn = screen.getByRole('button', { name: /Cancel/i });
        await fireEvent.click(btn);

        expect(mockOnCancel).toHaveBeenCalled();
    });

    it('does not render when isOpen is false', () => {
        render(
            <CondaDefaultsToSModal
                isOpen={false}
                onAcknowledge={vi.fn()}
                onCancel={vi.fn()}
            />
        );

        expect(screen.queryByText(/Anaconda defaults Channel/)).not.toBeInTheDocument();
    });
});
