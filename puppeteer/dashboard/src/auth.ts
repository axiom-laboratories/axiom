import { jwtDecode } from 'jwt-decode';

const API_URL = import.meta.env.VITE_API_URL || '/api'; // Use /api as default prefix

const TOKEN_KEY = 'mop_auth_token';

// Licence expired dialog state (managed globally; dialog renders in MainLayout)
let licenceExpiredDialogOpen = false;
let licenceExpiredDialogCallback: ((open: boolean) => void) | null = null;

export function setLicenceExpiredDialogCallback(callback: (open: boolean) => void) {
    licenceExpiredDialogCallback = callback;
}

export function showLicenceExpiredDialog() {
    licenceExpiredDialogOpen = true;
    if (licenceExpiredDialogCallback) {
        licenceExpiredDialogCallback(true);
    }
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    must_change_password?: boolean;
}

export interface UserJwt {
    sub: string;
    exp: number;
    username: string;
    role?: string;
}

export const login = async (username: string, password: string): Promise<LoginResponse> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);

    let res: Response;
    try {
        res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params,
            signal: controller.signal,
        });
    } catch (e: unknown) {
        clearTimeout(timeout);
        if (e instanceof Error && e.name === 'AbortError') {
            throw new Error('Connection timed out — is the server reachable?');
        }
        throw new Error('Network error — could not reach the server');
    }
    clearTimeout(timeout);

    if (!res.ok) {
        let detail = `Login failed (${res.status})`;
        try {
            const body = await res.json();
            if (body.detail) detail = body.detail;
        } catch { /* non-JSON error body */ }
        throw new Error(detail);
    }

    const data: LoginResponse = await res.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (data.must_change_password) {
        localStorage.setItem('mop_must_change_password', '1');
    } else {
        localStorage.removeItem('mop_must_change_password');
    }
    return data;
};

export const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = '/login';
};

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);

export const getUser = (): UserJwt | null => {
    const token = getToken();
    if (!token) return null;
    try {
        return jwtDecode<UserJwt>(token);
    } catch (e) {
        return null;
    }
};

export const authenticatedFetch = async (endpoint: string, options: RequestInit = {}): Promise<Response> => {
    const token = getToken();
    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string>),
        'Authorization': `Bearer ${token}`
    };

    // endpoint should be partial path like '/nodes' or full url?
    // Let's assume partial path if it starts with /
    const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

    const res = await fetch(url, { ...options, headers });

    // Handle 402 Licence Expired
    if (res.status === 402) {
        showLicenceExpiredDialog();
        throw new Error("Licence expired");
    }

    // Handle 401 Unauthorized
    if (res.status === 401) {
        logout();
    }
    return res;
};
