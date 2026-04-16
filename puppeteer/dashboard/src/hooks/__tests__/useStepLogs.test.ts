import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStepLogs } from '../useStepLogs';
import React from 'react';

// Mock authenticatedFetch
const mockAuthFetch = vi.fn();
vi.mock('../../auth', () => ({
  authenticatedFetch: (...args: any[]) => mockAuthFetch(...args),
}));

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

const createWrapper = () => {
  const queryClient = createQueryClient();
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useStepLogs Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables query when jobGuid is null', async () => {
    const { result } = renderHook(() => useStepLogs(null), {
      wrapper: createWrapper(),
    });

    // Should not be loading and no data
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toBeNull();

    // Verify fetch was never called
    expect(mockAuthFetch).not.toHaveBeenCalled();
  });

  it('disables query when jobGuid is undefined', async () => {
    const { result } = renderHook(() => useStepLogs(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(mockAuthFetch).not.toHaveBeenCalled();
  });

  it('fetches logs successfully for a valid jobGuid', async () => {
    const mockLogs = { stdout: 'output line 1\n', stderr: '' };
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockLogs,
    });

    const { result } = renderHook(() => useStepLogs('job-123'), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    // Wait for fetch to complete
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockLogs);
    expect(result.current.error).toBeNull();
    expect(mockAuthFetch).toHaveBeenCalledWith('/api/executions/job-123/logs');
  });

  it('handles 404 gracefully (step has no logs yet) by returning null data', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    const { result } = renderHook(() => useStepLogs('job-456'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 404 should result in null data, not an error
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('propagates other HTTP errors (500)', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useStepLogs('job-789'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toContain('500');
  });

  it('refetches when jobGuid changes', async () => {
    const mockLogs1 = { stdout: 'logs for job 1', stderr: '' };
    const mockLogs2 = { stdout: 'logs for job 2', stderr: '' };

    mockAuthFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockLogs1,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockLogs2,
      });

    const { result, rerender } = renderHook(
      ({ jobGuid }) => useStepLogs(jobGuid),
      {
        wrapper: createWrapper(),
        initialProps: { jobGuid: 'job-1' },
      }
    );

    // Wait for first fetch
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockLogs1);

    // Change jobGuid
    rerender({ jobGuid: 'job-2' });

    // Wait for second fetch
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockLogs2);
    expect(mockAuthFetch).toHaveBeenCalledTimes(2);
  });

  it('uses staleTime of 30000ms for caching', async () => {
    const mockLogs = { stdout: 'cached logs', stderr: '' };
    mockAuthFetch.mockResolvedValue({
      ok: true,
      json: async () => mockLogs,
    });

    const queryClient = createQueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children);

    const { result: result1 } = renderHook(() => useStepLogs('job-cache'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result1.current.isLoading).toBe(false);
    });

    // Call again with same jobGuid
    const { result: result2 } = renderHook(() => useStepLogs('job-cache'), {
      wrapper,
    });

    // Second query should use cache immediately (not loading)
    expect(result2.current.data).toEqual(mockLogs);
    expect(mockAuthFetch).toHaveBeenCalledTimes(1); // Only called once due to cache
  });
});
