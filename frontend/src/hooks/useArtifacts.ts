/**
 * React hook for querying and filtering generated deliverables.
 */

import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ArtifactMeta } from '../types';

export interface UseArtifactsResult {
  artifacts: ArtifactMeta[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  downloadArtifact: (artifactId: string) => void;
}

export function useArtifacts(): UseArtifactsResult {
  const [artifacts, setArtifacts] = useState<ArtifactMeta[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listArtifacts(100, 0);
      setArtifacts(list);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load artifacts';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadArtifact = useCallback((artifactId: string) => {
    const url = api.getArtifactDownloadUrl(artifactId);
    const link = document.createElement('a');
    link.href = url;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { artifacts, loading, error, refetch, downloadArtifact };
}