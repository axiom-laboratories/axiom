import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

// Mock useLicence — we control it per test
const mockUseLicence = vi.fn();
vi.mock('../../hooks/useLicence', () => ({
    useLicence: (...args: any[]) => mockUseLicence(...args),
}));

// Mock useFeatures to avoid fetching
vi.mock('../../hooks/useFeatures', () => ({
    useFeatures: () => ({
        foundry: true,
        rbac: true,
        service_principals: true,
        webhooks: true,
        audit: true,
    }),
}));

// Mock NotificationBell to avoid pulling in unrelated deps
vi.mock('../../components/NotificationBell', () => ({
    NotificationBell: () => null,
}));

// Mock getUser and logout — use vi.fn() so per-test overrides work
const mockGetUser = vi.fn();
vi.mock('../../auth', () => ({
    getUser: (...args: any[]) => mockGetUser(...args),
    logout: vi.fn(),
    authenticatedFetch: vi.fn(),
}));

import MainLayout from '../MainLayout';

const renderLayout = () =>
    render(
        <MemoryRouter>
            <MainLayout />
        </MemoryRouter>
    );

describe('MainLayout EE badge and grace/expired banner', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        sessionStorage.clear();
        mockGetUser.mockReturnValue({ username: 'admin', role: 'admin', sub: 'admin', exp: 9999999999 });
    });

    it('Test 11: badge shows EE with indigo classes when status is valid and isEnterprise is true', () => {
        mockUseLicence.mockReturnValue({
            status: 'valid',
            tier: 'enterprise',
            days_until_expiry: 90,
            node_limit: 50,
            customer_id: 'cust-1',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        const badge = screen.getByText('EE');
        expect(badge).toBeDefined();
        expect(badge.className).toContain('indigo');
    });

    it('Test 12: badge shows CE with zinc classes when status is ce and isEnterprise is false', () => {
        mockUseLicence.mockReturnValue({
            status: 'ce',
            tier: 'ce',
            days_until_expiry: 0,
            node_limit: 0,
            customer_id: null,
            grace_days: 0,
            isEnterprise: false,
        });

        renderLayout();

        const badge = screen.getByText('CE');
        expect(badge).toBeDefined();
        expect(badge.className).toContain('zinc');
    });

    it('Test 13: badge shows EE with amber classes and top banner is present when status is grace', () => {
        mockUseLicence.mockReturnValue({
            status: 'grace',
            tier: 'enterprise',
            days_until_expiry: 10,
            node_limit: 50,
            customer_id: 'cust-2',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        const badge = screen.getByText('EE');
        expect(badge).toBeDefined();
        expect(badge.className).toContain('amber');

        // Banner should be present with text about expiry
        expect(screen.getByText(/expires in 10 day/i)).toBeDefined();
    });

    it('Test 14: badge shows EE with red classes and top banner is present when status is expired', () => {
        mockUseLicence.mockReturnValue({
            status: 'expired',
            tier: 'enterprise',
            days_until_expiry: -5,
            node_limit: 50,
            customer_id: 'cust-3',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        const badge = screen.getByText('EE');
        expect(badge).toBeDefined();
        expect(badge.className).toContain('red');

        // Banner should be present with expired text
        expect(screen.getByText(/licence has expired/i)).toBeDefined();
    });

    it('Test 15: top banner is absent from DOM when status is valid', () => {
        mockUseLicence.mockReturnValue({
            status: 'valid',
            tier: 'enterprise',
            days_until_expiry: 90,
            node_limit: 50,
            customer_id: 'cust-1',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        // Neither grace nor expired banner text should appear
        expect(screen.queryByText(/expires in/i)).toBeNull();
        expect(screen.queryByText(/licence has expired/i)).toBeNull();
    });

    it('Test 16: operator sees no banner when status is grace', () => {
        mockGetUser.mockReturnValue({ username: 'op', role: 'operator', sub: 'op', exp: 9999999999 });
        mockUseLicence.mockReturnValue({
            status: 'grace',
            tier: 'enterprise',
            days_until_expiry: 10,
            node_limit: 50,
            customer_id: 'cust-2',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        expect(screen.queryByText(/expires in/i)).toBeNull();
    });

    it('Test 17: viewer sees no banner when status is expired', () => {
        mockGetUser.mockReturnValue({ username: 'v1', role: 'viewer', sub: 'v1', exp: 9999999999 });
        mockUseLicence.mockReturnValue({
            status: 'expired',
            tier: 'enterprise',
            days_until_expiry: -5,
            node_limit: 50,
            customer_id: 'cust-3',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        expect(screen.queryByText(/licence has expired/i)).toBeNull();
    });

    it('Test 18: admin can dismiss GRACE banner and it disappears', () => {
        mockUseLicence.mockReturnValue({
            status: 'grace',
            tier: 'enterprise',
            days_until_expiry: 10,
            node_limit: 50,
            customer_id: 'cust-2',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        // Banner should be visible before dismiss
        expect(screen.getByText(/expires in 10 day/i)).toBeDefined();

        // Click the dismiss button
        const dismissBtn = screen.getByRole('button', { name: /dismiss licence warning/i });
        fireEvent.click(dismissBtn);

        // Banner should be gone after dismiss
        expect(screen.queryByText(/expires in/i)).toBeNull();
    });

    it('Test 19: DEGRADED_CE banner has no dismiss button', () => {
        mockUseLicence.mockReturnValue({
            status: 'expired',
            tier: 'enterprise',
            days_until_expiry: -5,
            node_limit: 50,
            customer_id: 'cust-3',
            grace_days: 30,
            isEnterprise: true,
        });

        renderLayout();

        // Banner should be present
        expect(screen.getByText(/licence has expired/i)).toBeDefined();

        // No dismiss button should be present
        expect(screen.queryByRole('button', { name: /dismiss licence warning/i })).toBeNull();
    });
});
