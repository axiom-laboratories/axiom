import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApprovalQueuePanel } from '../ApprovalQueuePanel';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
    getUser: () => ({ username: 'testadmin', role: 'admin' }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn(),
        info: vi.fn(),
    },
}));

// Mock ResizeObserver (for recharts)
global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
};

window.HTMLElement.prototype.scrollIntoView = vi.fn();

const createQueryClient = () =>
    new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderWithProviders = (ui: React.ReactElement) =>
    render(
        <QueryClientProvider client={createQueryClient()}>
            {ui}
        </QueryClientProvider>
    );

const mockScriptAnalysisRequest = {
    id: 'req-1',
    requester_id: 'user-1',
    requester_username: 'operator1',
    package_name: 'requests',
    ecosystem: 'PYPI',
    detected_import: 'requests',
    status: 'PENDING' as const,
    created_at: new Date(Date.now() - 300000).toISOString(), // 5 mins ago
};

describe('ApprovalQueuePanel Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Permission Gating', () => {
        it('should render without permission error for admin users', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.queryByText(/Admin access required/i)).not.toBeInTheDocument();
            });
        });
    });

    describe('Tab Navigation', () => {
        it('should render all tabs: All, Pending, Approved, Rejected', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('tab', { name: /All Requests/i })).toBeInTheDocument();
                expect(screen.getByRole('tab', { name: /Pending/i })).toBeInTheDocument();
                expect(screen.getByRole('tab', { name: /Approved/i })).toBeInTheDocument();
                expect(screen.getByRole('tab', { name: /Rejected/i })).toBeInTheDocument();
            });
        });

        it('should start with Pending tab selected', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                const pendingTab = screen.getByRole('tab', { name: /Pending/i });
                expect(pendingTab).toHaveAttribute('aria-selected', 'true');
            });
        });

        it('should display badge counts on tabs', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        { ...mockScriptAnalysisRequest, status: 'PENDING' },
                        { ...mockScriptAnalysisRequest, id: 'req-2', status: 'PENDING' },
                        { ...mockScriptAnalysisRequest, id: 'req-3', status: 'APPROVED' },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText('3')).toBeInTheDocument(); // All Requests
            });
        });
    });

    describe('Request Loading & Display', () => {
        it('should show loader while fetching requests', () => {
            mockAuthFetch.mockImplementationOnce(
                () => new Promise(() => {}) // Never resolves
            );

            renderWithProviders(<ApprovalQueuePanel />);

            expect(screen.getByRole('progressbar', { hidden: true })).toBeInTheDocument();
        });

        it('should display empty state when no requests', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/All caught up/i)).toBeInTheDocument();
            });
        });

        it('should display error message on API failure', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: false,
                json: () => Promise.resolve({ detail: 'Server error' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/Failed to load requests/i)).toBeInTheDocument();
            });
        });

        it('should display requests in table with all columns', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText('operator1')).toBeInTheDocument();
                expect(screen.getByText('requests')).toBeInTheDocument();
                expect(screen.getByText('PYPI')).toBeInTheDocument();
                expect(screen.getByText('Pending')).toBeInTheDocument();
            });
        });
    });

    describe('Status Filtering', () => {
        it('should filter by Pending status', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        { ...mockScriptAnalysisRequest, status: 'PENDING' },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            const pendingTab = screen.getByRole('tab', { name: /Pending/i });
            fireEvent.click(pendingTab);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledWith(
                    expect.stringContaining('status=PENDING'),
                    expect.anything()
                );
            });
        });

        it('should filter by Approved status', async () => {
            mockAuthFetch.mockResolvedValue({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            const approvedTab = screen.getByRole('tab', { name: /Approved/i });
            fireEvent.click(approvedTab);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledWith(
                    expect.stringContaining('status=APPROVED'),
                    expect.anything()
                );
            });
        });

        it('should show all statuses when All tab is selected', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            const allTab = screen.getByRole('tab', { name: /All Requests/i });
            fireEvent.click(allTab);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledWith(
                    expect.not.stringContaining('status='),
                    expect.anything()
                );
            });
        });
    });

    describe('Approve Action', () => {
        it('should show Approve button for PENDING requests', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
            });
        });

        it('should not show Approve button for APPROVED requests', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            status: 'APPROVED',
                            reviewed_by: 'admin1',
                            reviewed_at: new Date().toISOString(),
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.queryByRole('button', { name: /Approve/i })).not.toBeInTheDocument();
                expect(screen.getByText('By admin1')).toBeInTheDocument();
            });
        });

        it('should call approve endpoint when Approve button is clicked', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'APPROVED' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
            });

            const approveBtn = screen.getByRole('button', { name: /Approve/i });
            fireEvent.click(approveBtn);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledWith(
                    '/api/analyzer/requests/req-1/approve',
                    expect.objectContaining({
                        method: 'POST',
                    })
                );
            });
        });

        it('should show success toast on approval', async () => {
            const { toast } = await import('sonner');

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'APPROVED' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
            });

            const approveBtn = screen.getByRole('button', { name: /Approve/i });
            fireEvent.click(approveBtn);

            await waitFor(() => {
                expect(toast.success).toHaveBeenCalledWith(
                    'Package approved successfully'
                );
            });
        });
    });

    describe('Reject Action', () => {
        it('should show Reject button for PENDING requests', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });
        });

        it('should open reject dialog when Reject button is clicked', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });

            const rejectBtn = screen.getByRole('button', { name: /Reject/i });
            fireEvent.click(rejectBtn);

            await waitFor(() => {
                expect(screen.getByRole('dialog')).toBeInTheDocument();
            });
        });

        it('should allow entering rejection reason in dialog', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });

            const rejectBtn = screen.getByRole('button', { name: /Reject/i });
            fireEvent.click(rejectBtn);

            const reasonInput = screen.getByPlaceholderText(/Rejection reason/i);
            fireEvent.change(reasonInput, { target: { value: 'Security vulnerability detected' } });

            expect(reasonInput).toHaveValue('Security vulnerability detected');
        });

        it('should call reject endpoint with reason', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'REJECTED' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });

            const rejectBtn = screen.getByRole('button', { name: /Reject/i });
            fireEvent.click(rejectBtn);

            const reasonInput = screen.getByPlaceholderText(/Rejection reason/i);
            fireEvent.change(reasonInput, { target: { value: 'Security concern' } });

            const confirmBtn = screen.getByRole('button', { name: /^Reject$/ });
            fireEvent.click(confirmBtn);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledWith(
                    '/api/analyzer/requests/req-1/reject',
                    expect.objectContaining({
                        method: 'POST',
                        body: expect.stringContaining('Security concern'),
                    })
                );
            });
        });

        it('should show success toast on rejection', async () => {
            const { toast } = await import('sonner');

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'REJECTED' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });

            const rejectBtn = screen.getByRole('button', { name: /Reject/i });
            fireEvent.click(rejectBtn);

            const confirmBtn = screen.getByRole('button', { name: /^Reject$/ });
            fireEvent.click(confirmBtn);

            await waitFor(() => {
                expect(toast.success).toHaveBeenCalledWith('Package rejected');
            });
        });

        it('should close dialog after successful rejection', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'REJECTED' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });

            const rejectBtn = screen.getByRole('button', { name: /Reject/i });
            fireEvent.click(rejectBtn);

            const confirmBtn = screen.getByRole('button', { name: /^Reject$/ });
            fireEvent.click(confirmBtn);

            await waitFor(() => {
                expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
            });
        });
    });

    describe('Rejected Request Display', () => {
        it('should display rejection reason and reviewer info', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            status: 'REJECTED',
                            reviewed_by: 'admin1',
                            review_reason: 'Contains malicious code',
                            reviewed_at: new Date().toISOString(),
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/Rejected by admin1/i)).toBeInTheDocument();
                expect(screen.getByText('Contains malicious code')).toBeInTheDocument();
            });
        });

        it('should not show action buttons for rejected requests', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            status: 'REJECTED',
                            reviewed_by: 'admin1',
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                const buttons = screen.queryAllByRole('button', { name: /Approve|Reject/i });
                expect(buttons.length).toBe(0);
            });
        });
    });

    describe('Date Formatting', () => {
        it('should display "just now" for very recent requests', async () => {
            const now = new Date();
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            created_at: now.toISOString(),
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/just now/i)).toBeInTheDocument();
            });
        });

        it('should display minutes ago for requests created minutes ago', async () => {
            const tenMinsAgo = new Date(Date.now() - 600000);
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            created_at: tenMinsAgo.toISOString(),
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/10m ago/i)).toBeInTheDocument();
            });
        });

        it('should display hours ago for requests created hours ago', async () => {
            const twoHoursAgo = new Date(Date.now() - 7200000);
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            created_at: twoHoursAgo.toISOString(),
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/2h ago/i)).toBeInTheDocument();
            });
        });

        it('should display days ago for requests created days ago', async () => {
            const threeDaysAgo = new Date(Date.now() - 259200000);
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () =>
                    Promise.resolve([
                        {
                            ...mockScriptAnalysisRequest,
                            created_at: threeDaysAgo.toISOString(),
                        },
                    ]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByText(/3d ago/i)).toBeInTheDocument();
            });
        });
    });

    describe('Error Handling', () => {
        it('should display error toast on approval failure', async () => {
            const { toast } = await import('sonner');

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: false,
                json: () => Promise.resolve({ detail: 'Approval failed' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
            });

            const approveBtn = screen.getByRole('button', { name: /Approve/i });
            fireEvent.click(approveBtn);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalled();
            });
        });

        it('should display error toast on rejection failure', async () => {
            const { toast } = await import('sonner');

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: false,
                json: () => Promise.resolve({ detail: 'Rejection failed' }),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
            });

            const rejectBtn = screen.getByRole('button', { name: /Reject/i });
            fireEvent.click(rejectBtn);

            const confirmBtn = screen.getByRole('button', { name: /^Reject$/ });
            fireEvent.click(confirmBtn);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalled();
            });
        });
    });

    describe('Query Invalidation', () => {
        it('should refresh requests after successful approval', async () => {
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'APPROVED' }),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([]),
            });

            renderWithProviders(<ApprovalQueuePanel />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
            });

            const approveBtn = screen.getByRole('button', { name: /Approve/i });
            fireEvent.click(approveBtn);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledTimes(3);
            });
        });

        it('should call onRefresh callback after successful action', async () => {
            const mockRefresh = vi.fn();

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([mockScriptAnalysisRequest]),
            });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: 'APPROVED' }),
            });

            renderWithProviders(<ApprovalQueuePanel onRefresh={mockRefresh} />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Approve/i })).toBeInTheDocument();
            });

            const approveBtn = screen.getByRole('button', { name: /Approve/i });
            fireEvent.click(approveBtn);

            await waitFor(() => {
                expect(mockRefresh).toHaveBeenCalled();
            });
        });
    });
});
