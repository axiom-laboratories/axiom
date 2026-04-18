import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authenticatedFetch } from '../auth';
import { toast } from 'sonner';

export interface VaultConfigResponse {
  vault_address: string;
  role_id: string;
  secret_id_masked: string;  // First 8 chars + "..."
  mount_path: string;
  namespace?: string;
  provider_type: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface VaultConfigUpdateRequest {
  vault_address?: string;
  role_id?: string;
  secret_id?: string;
  mount_path?: string;
  namespace?: string;
  provider_type?: string;
  enabled?: boolean;
}

export interface VaultTestConnectionRequest {
  vault_address: string;
  role_id: string;
  secret_id: string;
  mount_path?: string;
  namespace?: string;
}

export interface VaultTestConnectionResponse {
  success: boolean;
  status: 'healthy' | 'degraded' | 'disabled';
  error_detail?: string;
  message: string;
}

export interface VaultStatusResponse {
  status: 'healthy' | 'degraded' | 'disabled';
  vault_address: string;
  last_checked_at?: string;
  error_detail?: string;
  renewal_failures: number;
}

/**
 * Fetch current Vault configuration.
 */
export function useVaultConfig() {
  return useQuery<VaultConfigResponse, Error>({
    queryKey: ['vault', 'config'],
    queryFn: async () => {
      const response = await authenticatedFetch('/admin/vault/config', {
        method: 'GET',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch Vault config');
      }
      return response.json();
    },
    retry: 2,
    staleTime: 30000,  // 30 seconds
  });
}

/**
 * Update Vault configuration.
 */
export function useUpdateVaultConfig() {
  const queryClient = useQueryClient();

  return useMutation<VaultConfigResponse, Error, VaultConfigUpdateRequest>({
    mutationFn: async (data) => {
      const response = await authenticatedFetch('/admin/vault/config', {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update Vault config');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['vault', 'config'] });
      toast.success('Vault configuration updated');
    },
    onError: (error) => {
      toast.error(`Update failed: ${error.message}`);
    },
  });
}

/**
 * Test Vault connection with provided credentials (does not save).
 */
export function useTestVaultConnection() {
  return useMutation<VaultTestConnectionResponse, Error, VaultTestConnectionRequest>({
    mutationFn: async (data) => {
      const response = await authenticatedFetch('/admin/vault/test-connection', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Test connection failed');
      }
      return response.json();
    },
    onError: (error) => {
      toast.error(`Connection test failed: ${error.message}`);
    },
  });
}

/**
 * Fetch detailed Vault status.
 */
export function useVaultStatus() {
  return useQuery<VaultStatusResponse, Error>({
    queryKey: ['vault', 'status'],
    queryFn: async () => {
      const response = await authenticatedFetch('/admin/vault/status', {
        method: 'GET',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch Vault status');
      }
      return response.json();
    },
    retry: 2,
    refetchInterval: 10000,  // Refresh status every 10 seconds
  });
}
