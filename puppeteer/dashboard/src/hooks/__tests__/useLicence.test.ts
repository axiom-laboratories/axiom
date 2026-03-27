import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useLicence } from '../useLicence';

// Mock authenticatedFetch to control API responses
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
    authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

const makeResponse = (data: object) => ({
    ok: true,
    json: async () => data,
});

const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useLicence hook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('Test 1: maps all backend fields + computes isEnterprise:true for valid enterprise licence', async () => {
        mockAuthFetch.mockResolvedValueOnce(makeResponse({
            status: 'valid',
            tier: 'enterprise',
            days_until_expiry: 90,
            node_limit: 50,
            customer_id: 'cust-1',
            grace_days: 30,
        }));

        const { result } = renderHook(() => useLicence(), { wrapper: createWrapper() });

        await waitFor(() => {
            expect(result.current.status).toBe('valid');
        });

        expect(result.current.tier).toBe('enterprise');
        expect(result.current.days_until_expiry).toBe(90);
        expect(result.current.node_limit).toBe(50);
        expect(result.current.customer_id).toBe('cust-1');
        expect(result.current.grace_days).toBe(30);
        expect(result.current.isEnterprise).toBe(true);
    });

    it('Test 2: isEnterprise is false when status is ce', async () => {
        mockAuthFetch.mockResolvedValueOnce(makeResponse({
            status: 'ce',
            tier: 'ce',
            days_until_expiry: 0,
            node_limit: 0,
            customer_id: null,
            grace_days: 0,
        }));

        const { result } = renderHook(() => useLicence(), { wrapper: createWrapper() });

        await waitFor(() => {
            expect(result.current.status).toBe('ce');
        });

        expect(result.current.isEnterprise).toBe(false);
    });

    it('Test 3: isEnterprise is true when status is grace', async () => {
        mockAuthFetch.mockResolvedValueOnce(makeResponse({
            status: 'grace',
            tier: 'enterprise',
            days_until_expiry: 10,
            node_limit: 50,
            customer_id: 'cust-2',
            grace_days: 30,
        }));

        const { result } = renderHook(() => useLicence(), { wrapper: createWrapper() });

        await waitFor(() => {
            expect(result.current.status).toBe('grace');
        });

        expect(result.current.isEnterprise).toBe(true);
    });

    it('Test 4: isEnterprise is true when status is expired (EE-licenced, just expired)', async () => {
        mockAuthFetch.mockResolvedValueOnce(makeResponse({
            status: 'expired',
            tier: 'enterprise',
            days_until_expiry: -5,
            node_limit: 50,
            customer_id: 'cust-3',
            grace_days: 30,
        }));

        const { result } = renderHook(() => useLicence(), { wrapper: createWrapper() });

        await waitFor(() => {
            expect(result.current.status).toBe('expired');
        });

        expect(result.current.isEnterprise).toBe(true);
    });
});
