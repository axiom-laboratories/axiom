import { jwtDecode } from "jwt-decode"; // Correct named import for v4

export const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch('https://localhost:8001/auth/login', {
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

export const authenticatedFetch = async (url, options = {}) => {
    const token = getToken();
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };

    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        logout();
    }
    return res;
};
