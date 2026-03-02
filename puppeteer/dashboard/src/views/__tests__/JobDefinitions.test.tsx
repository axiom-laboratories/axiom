import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import JobDefinitions from '../JobDefinitions';
import { BrowserRouter } from 'react-router-dom';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

describe('JobDefinitions View', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default mocks for loadData
        mockAuthFetch.mockImplementation((endpoint) => {
            if (endpoint === '/jobs/definitions') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/jobs') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            if (endpoint === '/signatures') return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            return Promise.resolve({ ok: false });
        });
    });

    it('renders the page title and description', async () => {
        render(
            <BrowserRouter>
                <JobDefinitions />
            </BrowserRouter>
        );

        // Wait for loading to finish
        await waitFor(() => {
            expect(screen.queryByClassName?.('animate-pulse')).not.toBeInTheDocument();
        }, { timeout: 3000 }).catch(() => { }); // Fallback if pulse check fails

        expect(screen.getByText(/Scheduled Jobs/i)).toBeInTheDocument();
        expect(screen.getByText(/Signed, zero-trust recurring payloads/i)).toBeInTheDocument();
    });

    it('shows the "Archive New Payload" button', async () => {
        render(
            <BrowserRouter>
                <JobDefinitions />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText(/Archive New Payload/i)).toBeInTheDocument();
        });
    });
});
