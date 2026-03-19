import { useQuery } from '@tanstack/react-query';
import { authenticatedFetch } from '../auth';

export interface Features {
  audit: boolean;
  foundry: boolean;
  webhooks: boolean;
  triggers: boolean;
  rbac: boolean;
  resource_limits: boolean;
  service_principals: boolean;
  api_keys: boolean;
}

const CE_DEFAULTS: Features = {
  audit: false,
  foundry: false,
  webhooks: false,
  triggers: false,
  rbac: false,
  resource_limits: false,
  service_principals: false,
  api_keys: false,
};

export function useFeatures(): Features {
  const { data } = useQuery<Features>({
    queryKey: ['features'],
    queryFn: async () => {
      const res = await authenticatedFetch('/api/features');
      if (!res.ok) return CE_DEFAULTS;
      return res.json();
    },
    staleTime: 5 * 60 * 1000, // cache 5 minutes
    retry: false,
  });
  return data ?? CE_DEFAULTS;
}
