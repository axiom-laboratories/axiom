import { jwtDecode } from "jwt-decode";

const API_URL = import.meta.env.VITE_API_URL || ''; // Default to relative if not provided

export const login = async (username: string, password: string): Promise<any> => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        body: formData
    });

    if (!res.ok) throw new Error("Login failed");

    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    return data;
};

export const logout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
};

export const getToken = () => localStorage.getItem('token');

export const getUser = () => {
    const token = getToken();
    if (!token) return null;
    try {
        return jwtDecode(token);
    } catch (e) {
        return null;
    }
};

export const authenticatedFetch = async (endpoint: string, options: RequestInit = {}): Promise<Response> => {
    const token = getToken();
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    } as any;

    // endpoint should be partial path like '/nodes' or full url?
    // Let's assume partial path if it starts with /
    const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        logout();
    }
    return res;
};
