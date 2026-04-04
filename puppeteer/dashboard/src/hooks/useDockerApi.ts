/**
 * Custom hook for Docker provisioning API calls (start/stop mirror containers).
 * Manages service state, handles errors, auto-polls status every 5s.
 *
 * @param serviceName - Name of service (pypi, apt, apk, npm, nuget, oci_hub, oci_ghcr, conda)
 * @returns { startService, stopService, getStatus, status, isLoading, error }
 */

import { useState, useEffect, useCallback } from 'react';
import { authenticatedFetch } from '../auth';

export type ServiceStatus = 'running' | 'stopped' | 'error' | 'unknown';

interface UseDockerApiResult {
  status: ServiceStatus;
  isLoading: boolean;
  error: string | null;
  startService: () => Promise<void>;
  stopService: () => Promise<void>;
}

export function useDockerApi(serviceName: string): UseDockerApiResult {
  const [status, setStatus] = useState<ServiceStatus>('unknown');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch current status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await authenticatedFetch('/api/admin/mirror-provision/status');

      if (!response.ok) {
        if (response.status === 403) {
          setError('Docker service provisioning disabled. Set ALLOW_CONTAINER_MANAGEMENT=true to use this feature.');
          setStatus('error');
          return;
        }
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }

      const data = await response.json() as Record<string, string>;
      const newStatus = (data[serviceName] || 'unknown') as ServiceStatus;
      setStatus(newStatus);
      setError(null);
    } catch (err) {
      console.error(`Error fetching status for ${serviceName}:`, err);
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  }, [serviceName]);

  // Auto-poll status every 5s
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Start service
  const startService = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        `/api/admin/mirror-provision/${serviceName}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'start' }),
        }
      );

      if (response.status === 403) {
        setError('Docker service provisioning disabled. Set ALLOW_CONTAINER_MANAGEMENT=true to use this feature.');
        setStatus('error');
        return;
      }

      if (!response.ok) {
        const data = await response.json() as { detail?: string };
        throw new Error(data.detail || `Failed to start service: ${response.statusText}`);
      }

      setStatus('running');
      await fetchStatus();
    } catch (err) {
      setStatus('error');
      const errorMsg = err instanceof Error ? err.message : 'Failed to start service';
      setError(errorMsg);
      console.error(`Error starting ${serviceName}:`, err);
    } finally {
      setIsLoading(false);
    }
  }, [serviceName, fetchStatus]);

  // Stop service
  const stopService = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        `/api/admin/mirror-provision/${serviceName}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'stop' }),
        }
      );

      if (!response.ok) {
        const data = await response.json() as { detail?: string };
        throw new Error(data.detail || `Failed to stop service: ${response.statusText}`);
      }

      setStatus('stopped');
      await fetchStatus();
    } catch (err) {
      setStatus('error');
      const errorMsg = err instanceof Error ? err.message : 'Failed to stop service';
      setError(errorMsg);
      console.error(`Error stopping ${serviceName}:`, err);
    } finally {
      setIsLoading(false);
    }
  }, [serviceName, fetchStatus]);

  return {
    status,
    isLoading,
    error,
    startService,
    stopService,
  };
}
