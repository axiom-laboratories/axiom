import { jwtDecode } from "jwt-decode";

const API_URL = import.meta.env.VITE_API_URL || '/api'; // Use /api as default prefix

export interface LoginResponse {
    access_token: string;
    token_type: string;
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

    const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: params
    });

    if (!res.ok) throw new Error("Login failed");

    const data: LoginResponse = await res.json();
    localStorage.setItem('token', data.access_token);
    return data;
};

export const logout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
};

export const getToken = () => localStorage.getItem('token');

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
    if (res.status === 401) {
        logout();
    }
    return res;
};
