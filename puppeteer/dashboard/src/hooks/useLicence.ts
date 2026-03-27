import { useQuery } from '@tanstack/react-query';
import { authenticatedFetch } from '../auth';

export interface LicenceInfo {
  status: 'valid' | 'grace' | 'expired' | 'ce';
  tier: string;
  days_until_expiry: number;
  node_limit: number;
  customer_id: string | null;
  grace_days: number;
  isEnterprise: boolean;  // computed: status !== 'ce'
}

const CE_DEFAULTS: Omit<LicenceInfo, 'isEnterprise'> = {
  status: 'ce',
  tier: 'ce',
  days_until_expiry: 0,
  node_limit: 0,
  customer_id: null,
  grace_days: 0,
};

export function useLicence(): LicenceInfo {
  const { data } = useQuery<Omit<LicenceInfo, 'isEnterprise'>>({
    queryKey: ['licence'],
    queryFn: async () => {
      const res = await authenticatedFetch('/api/licence');
      if (!res.ok) return CE_DEFAULTS;
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const raw = data ?? CE_DEFAULTS;
  return { ...raw, isEnterprise: raw.status !== 'ce' };
}
