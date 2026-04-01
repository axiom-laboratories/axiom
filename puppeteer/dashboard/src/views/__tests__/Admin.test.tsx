import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

// Mock authenticatedFetch to prevent network calls
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
    getUser: () => ({ username: 'admin', role: 'admin' }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

// Mock useLicence — we control it per test using vi.mocked
const mockUseLicence = vi.fn();
vi.mock('../../hooks/useLicence', () => ({
    useLicence: (...args: any[]) => mockUseLicence(...args),
}));

// Import after mocks are set up
import Admin from '../Admin';

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

const enterpriseLicence = (overrides = {}) => ({
    status: 'valid' as const,
    tier: 'enterprise',
    days_until_expiry: 90,
    node_limit: 50,
    customer_id: 'cust-1',
    grace_days: 30,
    isEnterprise: true,
    ...overrides,
});

const ceLicence = () => ({
    status: 'ce' as const,
    tier: 'ce',
    days_until_expiry: 0,
    node_limit: 0,
    customer_id: null,
    grace_days: 0,
    isEnterprise: false,
});

describe('Admin LicenceSection', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default mock for all authenticated fetches
        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: async () => [],
        });
    });

    it('Test 5: shows Enterprise tier badge and Active status badge for valid enterprise licence', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence());

        renderWithProviders(<Admin />);

        expect(screen.getByText('Enterprise')).toBeDefined();
        expect(screen.queryByText('Community')).toBeNull();
        expect(screen.getByText('Active')).toBeDefined();
    });

    it('Test 6: shows Community tier, hides node_limit row, and shows CE upgrade hint for ce status', () => {
        mockUseLicence.mockReturnValue(ceLicence());

        renderWithProviders(<Admin />);

        // Both Edition and Status rows show Community for CE
        const communityElements = screen.getAllByText('Community');
        expect(communityElements.length).toBeGreaterThanOrEqual(1);
        // Node limit row should be hidden
        expect(screen.queryByText('Node limit')).toBeNull();
        // CE upgrade hint should be visible
        expect(screen.getByText(/AXIOM_LICENCE_KEY/)).toBeDefined();
    });

    it('Test 7: shows Grace Period status badge (amber) and an expiry date string when status is grace', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence({
            status: 'grace' as const,
            days_until_expiry: 10,
            isEnterprise: true,
        }));

        renderWithProviders(<Admin />);

        expect(screen.getByText('Grace Period')).toBeDefined();
        // Should NOT show the literal string 'Expired' for a grace status
        // It should show a date string instead
        const expiryRow = screen.queryByText('Expired');
        expect(expiryRow).toBeNull();
    });

    it('Test 8: shows Expired status badge and Expired text (not a date) when status is expired', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence({
            status: 'expired' as const,
            days_until_expiry: -5,
            isEnterprise: true,
        }));

        renderWithProviders(<Admin />);

        // The status badge should show 'Expired'
        const expiredElements = screen.getAllByText('Expired');
        // At least one instance for the status badge, and one for the expiry value
        expect(expiredElements.length).toBeGreaterThanOrEqual(2);
    });

    it('Test 9: shows Node limit row with value 50 for valid enterprise licence with node_limit:50', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence({ node_limit: 50 }));

        renderWithProviders(<Admin />);

        expect(screen.getByText('Node limit')).toBeDefined();
        expect(screen.getByText('50')).toBeDefined();
    });

    it('Test 10: features chip list is absent from the licence section DOM', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence());

        renderWithProviders(<Admin />);

        // The old features list would have a "Features" label — it must not exist
        expect(screen.queryByText('Features')).toBeNull();
    });
});

describe('Tab visibility by licence tier', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAuthFetch.mockResolvedValue({
            ok: true,
            json: async () => [],
        });
    });

    it('hides EE tabs in CE mode', () => {
        mockUseLicence.mockReturnValue(ceLicence());
        renderWithProviders(<Admin />);

        expect(screen.queryByRole('tab', { name: /smelter registry/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: /bom explorer/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: /tools/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: /artifact vault/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: /rollouts/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: /automation/i })).not.toBeInTheDocument();
    });

    it('shows Enterprise upgrade tab in CE mode', () => {
        mockUseLicence.mockReturnValue(ceLicence());
        renderWithProviders(<Admin />);

        expect(screen.getByRole('tab', { name: /enterprise/i })).toBeInTheDocument();
    });

    it('shows all EE tabs in EE mode', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence());
        renderWithProviders(<Admin />);

        expect(screen.getByRole('tab', { name: /smelter registry/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /bom explorer/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /tools/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /artifact vault/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /rollouts/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /automation/i })).toBeInTheDocument();
    });

    it('does not show Enterprise upgrade tab in EE mode', () => {
        mockUseLicence.mockReturnValue(enterpriseLicence());
        renderWithProviders(<Admin />);

        expect(screen.queryByRole('tab', { name: /^\+ enterprise$/i })).not.toBeInTheDocument();
    });

    it('CE mode: Onboarding tab content renders and no EE TabsContent is shown (CEUX-03)', () => {
        mockUseLicence.mockReturnValue(ceLicence());
        renderWithProviders(<Admin />);

        // Default tab (Onboarding) must render its content — not a blank page
        expect(screen.getByText('Node Enrollment')).toBeInTheDocument();

        // None of the six EE TabsContent blocks render any content in CE mode.
        // Each EE TabsContent is gated with {isEnterprise && (...)} so these
        // feature-specific headings must be absent from the DOM.
        expect(screen.queryByText('Smelter Registry')).not.toBeInTheDocument();
        expect(screen.queryByText('BOM Explorer')).not.toBeInTheDocument();
        expect(screen.queryByText('Artifact Vault')).not.toBeInTheDocument();
        expect(screen.queryByText('Rollouts')).not.toBeInTheDocument();
        expect(screen.queryByText('Automation')).not.toBeInTheDocument();
    });
});
