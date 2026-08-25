/**
 * React hook for querying local model registry and Ollama availability.
 */

import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ModelInfo } from '../types';

export interface UseModelsResult {
  models: ModelInfo[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useModels(): UseModelsResult {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listModels();
      setModels(res.models || []);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load models';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { models, loading, error, refetch };
}