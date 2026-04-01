import { useEffect, useRef, useCallback } from 'react';
import { getToken } from '../auth';

type WsHandler = (event: string, data: unknown) => void;

/**
 * Opens a WebSocket to /ws (backend URL resolved from window.location).
 * Calls onMessage whenever a JSON frame arrives.
 * Automatically reconnects on close/error with exponential back-off.
 * Sends a ping every 20 s to keep the connection alive through proxies.
 */
export function useWebSocket(onMessage: WsHandler) {
    const wsRef = useRef<WebSocket | null>(null);
    const retryRef = useRef<ReturnType<typeof setTimeout>>();
    const pingRef = useRef<ReturnType<typeof setInterval>>();
    const mountedRef = useRef(true);
    const delayRef = useRef(1000);
    const handlerRef = useRef(onMessage);
    handlerRef.current = onMessage;

    const connect = useCallback(() => {
        if (!mountedRef.current) return;

        // Derive the WS URL from the page origin (http→ws, https→wss)
        const origin = window.location.origin.replace(/^http/, 'ws');
        // The backend is at :8001 in dev (proxied via vite) or at same origin in prod
        const backendBase = import.meta.env.VITE_API_BASE ?? '';
        const base = `${backendBase.replace(/^http/, 'ws')}/ws`.replace(/^\/ws/, `${origin}/ws`);
        const url = base.startsWith('ws') ? base : `${origin}/ws`;

        // Pass JWT as query param — browsers don't support custom headers on WS upgrade
        const token = getToken();
        const ws = new WebSocket(token ? `${url}?token=${encodeURIComponent(token)}` : url);
        wsRef.current = ws;

        ws.onopen = () => {
            delayRef.current = 1000; // reset back-off
            // Keepalive ping — stored in ref so cleanup can clear it explicitly
            clearInterval(pingRef.current);
            pingRef.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) ws.send('ping');
                else clearInterval(pingRef.current);
            }, 20_000);
        };

        ws.onmessage = (e) => {
            try {
                const { event, data } = JSON.parse(e.data);
                handlerRef.current(event, data);
            } catch { /* pong or unexpected frame */ }
        };

        // onerror always fires immediately before onclose — using the same handler for
        // both would schedule two retries and orphan the first timer. Keep onerror as a
        // no-op and let onclose be the single scheduling point.
        ws.onerror = () => { /* handled by onclose */ };

        ws.onclose = () => {
            clearInterval(pingRef.current);
            if (!mountedRef.current) return;
            retryRef.current = setTimeout(() => {
                delayRef.current = Math.min(delayRef.current * 2, 30_000);
                connect();
            }, delayRef.current);
        };
    }, []);

    useEffect(() => {
        mountedRef.current = true;
        connect();
        return () => {
            mountedRef.current = false;
            clearTimeout(retryRef.current);
            clearInterval(pingRef.current);
            wsRef.current?.close();
        };
    }, [connect]);
}
