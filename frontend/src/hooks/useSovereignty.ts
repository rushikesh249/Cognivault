/**
 * React hook for live Sovereignty Status telemetry polling.
 */

import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { SovereigntyStatus } from '../types';

export interface UseSovereigntyResult {
  data: SovereigntyStatus | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useSovereignty(pollIntervalMs = 5000): UseSovereigntyResult {
  const [data, setData] = useState<SovereigntyStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      const status = await api.getSovereigntyStatus();
      setData(status);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to query sovereignty status';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
    const interval = setInterval(refetch, pollIntervalMs);
    return () => clearInterval(interval);
  }, [refetch, pollIntervalMs]);

  return { data, loading, error, refetch };
}