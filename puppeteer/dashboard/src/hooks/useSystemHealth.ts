import { useState, useEffect } from 'react';

interface SystemHealth {
  status: string;
  mirrors_available: boolean;
  [key: string]: any;
}

export function useSystemHealth(pollInterval: number = 30000) {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch('/api/system/health', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('mop_auth_token')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setHealth(data);
        }
      } catch (error) {
        console.warn('Failed to fetch system health:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, pollInterval);
    return () => clearInterval(interval);
  }, [pollInterval]);

  return { health, isLoading };
}
