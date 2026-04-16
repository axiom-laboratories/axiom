import { useQuery } from '@tanstack/react-query';
import { authenticatedFetch } from '@/auth';

/**
 * Hook for fetching step execution logs via the /api/executions/{job_guid}/logs endpoint.
 *
 * Accepts an optional job_guid from a WorkflowStepRun. If null/undefined (for unrun steps),
 * the query is disabled and no fetch is attempted.
 *
 * @param jobGuid - The job GUID from a WorkflowStepRun (null/undefined for PENDING/SKIPPED/CANCELLED steps)
 * @returns Object with { data, isLoading, error }
 *   - data: { stdout: string, stderr: string } or null if step has no logs or is not run yet
 *   - isLoading: boolean indicating fetch in progress
 *   - error: Error object if fetch failed (404 treated as null data, not an error)
 *
 * @example
 * const { data, isLoading, error } = useStepLogs(stepRun.job_guid);
 * if (isLoading) return <Spinner />;
 * if (error) return <div>Failed to load logs</div>;
 * return <pre>{data?.stdout}</pre>;
 */
export const useStepLogs = (jobGuid: string | null | undefined) => {
  return useQuery({
    queryKey: ['step-logs', jobGuid],
    queryFn: async () => {
      if (!jobGuid) return null;

      const res = await authenticatedFetch(`/api/executions/${jobGuid}/logs`);

      // 404 means step has no logs yet — treat as null data, not an error
      if (res.status === 404) {
        return null;
      }

      if (!res.ok) {
        throw new Error(`Failed to fetch logs: ${res.status}`);
      }

      return res.json() as Promise<{ stdout: string; stderr: string }>;
    },
    enabled: !!jobGuid, // Only run query if jobGuid is provided
    staleTime: 30000, // Cache for 30 seconds
  });
};
