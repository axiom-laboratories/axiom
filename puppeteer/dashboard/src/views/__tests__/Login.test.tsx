import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Login from '../Login';
import { BrowserRouter } from 'react-router-dom';

// Mock the auth module
vi.mock('../../auth', () => ({
    login: vi.fn(),
}));

describe('Login Component', () => {
    it('renders the login form', () => {
        render(
            <BrowserRouter>
                <Login />
            </BrowserRouter>
        );

        expect(screen.getByText(/System Login/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/admin/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Enter Control Plane/i })).toBeInTheDocument();
    });
});
