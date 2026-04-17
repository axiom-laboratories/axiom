import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { authenticatedFetch, showLicenceExpiredDialog, setLicenceExpiredDialogCallback } from '../auth';

// Mock localStorage
const localStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => {
            store[key] = value.toString();
        },
        removeItem: (key: string) => {
            delete store[key];
        },
        clear: () => {
            store = {};
        },
    };
})();

Object.defineProperty(global, 'localStorage', {
    value: localStorageMock,
});

describe('FEBE-01: authenticatedFetch 402 handler', () => {
    beforeEach(() => {
        localStorageMock.clear();
        localStorageMock.setItem('mop_auth_token', 'test-token-123');
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('should intercept 402 Licence Expired response', async () => {
        let dialogWasShown = false;

        // Set up callback to track dialog state
        setLicenceExpiredDialogCallback((open: boolean) => {
            dialogWasShown = open;
        });

        // Mock fetch to return 402
        global.fetch = vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({ detail: 'Licence expired' }), {
                    status: 402,
                    headers: { 'Content-Type': 'application/json' },
                })
            )
        );

        try {
            await authenticatedFetch('/api/some-route');
        } catch (e) {
            // Expected to throw after showing dialog
        }

        // Verify dialog was triggered
        expect(dialogWasShown).toBe(true);
    });

    it('should throw error after showing 402 dialog', async () => {
        global.fetch = vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({ detail: 'Licence expired' }), {
                    status: 402,
                })
            )
        );

        let caughtError: Error | null = null;
        try {
            await authenticatedFetch('/api/some-route');
        } catch (e) {
            caughtError = e as Error;
        }

        expect(caughtError).not.toBeNull();
        expect(caughtError?.message).toContain('Licence expired');
    });

    it('should handle 200 OK response normally', async () => {
        global.fetch = vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({ data: 'success' }), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' },
                })
            )
        );

        const response = await authenticatedFetch('/api/some-route');

        expect(response.ok).toBe(true);
        expect(response.status).toBe(200);
    });

    it('should include Authorization header with Bearer token', async () => {
        const fetchSpy = vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({}), { status: 200 })
            )
        );
        global.fetch = fetchSpy;

        await authenticatedFetch('/api/test');

        expect(fetchSpy).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({
                headers: expect.objectContaining({
                    Authorization: 'Bearer test-token-123',
                }),
            })
        );
    });

    it('should handle 401 Unauthorized by logging out', async () => {
        // Mock window.location.href
        delete (window as any).location;
        window.location = { href: '' } as any;

        global.fetch = vi.fn(() =>
            Promise.resolve(
                new Response(JSON.stringify({ detail: 'Unauthorized' }), {
                    status: 401,
                })
            )
        );

        try {
            await authenticatedFetch('/api/some-route');
        } catch (e) {
            // Expected
        }

        // Verify logout redirect was triggered
        expect(window.location.href).toBe('/login');
    });

    it('showLicenceExpiredDialog should trigger callback', () => {
        let dialogOpen = false;

        setLicenceExpiredDialogCallback((open: boolean) => {
            dialogOpen = open;
        });

        showLicenceExpiredDialog();

        expect(dialogOpen).toBe(true);
    });
});
