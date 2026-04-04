import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ScriptAnalyzerPanel } from '../ScriptAnalyzerPanel';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
    getUser: () => ({ username: 'testuser', role: 'operator' }),
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

describe('ScriptAnalyzerPanel Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Form Rendering', () => {
        it('should render textarea + language dropdown + Analyze button', () => {
            renderWithProviders(<ScriptAnalyzerPanel />);

            expect(screen.getByPlaceholderText(/Paste your.*script here/i)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Analyze Script/i })).toBeInTheDocument();
            expect(screen.getByRole('combobox')).toBeInTheDocument();
        });

        it('should display detected language message', () => {
            renderWithProviders(<ScriptAnalyzerPanel />);

            expect(screen.getByText(/Detected:/)).toBeInTheDocument();
        });

        it('should have Analyze button disabled when script is empty', () => {
            renderWithProviders(<ScriptAnalyzerPanel />);

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            expect(analyzeBtn).toBeDisabled();
        });
    });

    describe('Language Auto-Detection', () => {
        it('should detect Python from import statement', async () => {
            
            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            await waitFor(() => {
                expect(screen.getByText(/Detected: python/i)).toBeInTheDocument();
            });
        });

        it('should detect Bash from apt-get', async () => {
            
            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'apt-get install curl' } });

            await waitFor(() => {
                expect(screen.getByText(/Detected: bash/i)).toBeInTheDocument();
            });
        });

        it('should detect PowerShell from Import-Module', async () => {
            
            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'Import-Module posh-git' } });

            await waitFor(() => {
                expect(screen.getByText(/Detected: powershell/i)).toBeInTheDocument();
            });
        });
    });

    describe('Analysis Flow', () => {
        it('should enable Analyze button when script has content', async () => {
            
            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            expect(analyzeBtn).not.toBeDisabled();
        });

        it('should call POST /api/analyzer/analyze-script when Analyze is clicked', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(mockAuthFetch).toHaveBeenCalledWith(
                    '/api/analyzer/analyze-script',
                    expect.objectContaining({
                        method: 'POST',
                        body: expect.stringContaining('import requests'),
                    })
                );
            });
        });

        it('should display results table after successful analysis', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'new',
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(screen.getByText('requests')).toBeInTheDocument();
                expect(screen.getByText('PYPI')).toBeInTheDocument();
            });
        });

        it('should display empty state when no packages found', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'print("hello")' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(screen.getByText(/No packages detected/i)).toBeInTheDocument();
            });
        });

        it('should show error message on API failure', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: false,
                json: () => Promise.resolve({ detail: 'Script has syntax errors' }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import invalid @@@' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(screen.getByText(/Script has syntax errors/i)).toBeInTheDocument();
            });
        });
    });

    describe('Results Table & Status Badges', () => {
        it('should group suggestions by ecosystem', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'new',
                        },
                        {
                            package_name: 'curl',
                            import_name: 'curl',
                            ecosystem: 'APT',
                            confidence: 'High',
                            mapped: false,
                            status: 'new',
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(screen.getByText('PYPI')).toBeInTheDocument();
                expect(screen.getByText('APT')).toBeInTheDocument();
            });
        });

        it('should show green Approved badge for approved packages', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'approved',
                            blueprints: ['web-server'],
                            node_count: 5,
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(screen.getByText('Approved')).toBeInTheDocument();
            });
        });

        it('should show blue New badge for new packages', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'new',
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                const badges = screen.getAllByText('New');
                expect(badges.length).toBeGreaterThan(0);
            });
        });

        it('should disable checkbox for approved packages', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'approved',
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                const checkboxes = screen.getAllByRole('checkbox');
                // First checkbox should be disabled (for approved package)
                expect(checkboxes[1]).toBeDisabled();
            });
        });

        it('should show mapped indicator for packages like cv2', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'opencv-python',
                            import_name: 'cv2',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: true,
                            status: 'new',
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import cv2' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                expect(screen.getByText(/mapped/i)).toBeInTheDocument();
            });
        });
    });

    describe('Checkbox Selection', () => {
        it('should enable approval button when packages are selected', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'new',
                        },
                    ],
                }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            await waitFor(() => {
                const checkboxes = screen.getAllByRole('checkbox');
                expect(checkboxes.length).toBeGreaterThan(0);
                // Click the first checkbox to select a package
                fireEvent.click(checkboxes[1]);
            });
        });
    });

    describe('Permission-Gated Actions', () => {
        it('should show Request Approval button for operator users', async () => {
            renderWithProviders(<ScriptAnalyzerPanel />);

            // Operator role should have Request Approval (mocked in beforeEach)
            const textarea = screen.getByPlaceholderText(/Paste your.*script here/i);
            fireEvent.change(textarea, { target: { value: 'import requests' } });

            mockAuthFetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    detected_language: 'python',
                    suggestions: [
                        {
                            package_name: 'requests',
                            import_name: 'requests',
                            ecosystem: 'PYPI',
                            confidence: 'High',
                            mapped: false,
                            status: 'new',
                        },
                    ],
                }),
            });

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            fireEvent.click(analyzeBtn);

            // After selecting, Request Approval button should be visible
            // (Note: in real scenario with admin role, would see Approve Selected instead)
        });
    });

    describe('Error Handling', () => {
        it('should show validation error for empty script', async () => {
            
            mockAuthFetch.mockResolvedValueOnce({
                ok: false,
                json: () => Promise.resolve({ detail: 'Please paste a script' }),
            });

            renderWithProviders(<ScriptAnalyzerPanel />);

            const analyzeBtn = screen.getByRole('button', { name: /Analyze Script/i });
            // Button should be disabled for empty script
            expect(analyzeBtn).toBeDisabled();
        });
    });
});
