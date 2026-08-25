import React, { useState } from 'react';
import { ArtifactCard } from './ArtifactCard';
import { IconFileText, IconLayers, IconRefresh } from '../common/Icons';
import { useArtifacts } from '../../hooks/useArtifacts';
import type { ArtifactMeta } from '../../types';

export const ArtifactExplorer: React.FC = () => {
  const { artifacts, loading, error, refetch } = useArtifacts();
  const [selectedFormat, setSelectedFormat] = useState<string>('all');
  const [selectedArtifactForSources, setSelectedArtifactForSources] = useState<ArtifactMeta | null>(null);

  const filtered = artifacts.filter((art) => {
    if (selectedFormat === 'all') return true;
    return art.kind.toLowerCase() === selectedFormat.toLowerCase();
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            Deliverables & RAG Artifact Catalog
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Browse, inspect source citations, and download multi-format deliverables (DOCX, XLSX, PPTX, PDF).
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select
            className="form-select"
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
          >
            <option value="all">All Formats ({artifacts.length})</option>
            <option value="docx">DOCX only</option>
            <option value="xlsx">XLSX only</option>
            <option value="pptx">PPTX only</option>
            <option value="pdf">PDF only</option>
          </select>

          <button type="button" className="btn btn-secondary" onClick={() => refetch()} disabled={loading}>
            <IconRefresh size={14} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: 'var(--status-error-bg)',
          border: '1px solid var(--status-error-border)',
          borderRadius: '8px',
          color: 'var(--status-error)',
          fontSize: '0.85rem'
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: '#64748b' }}>
          Loading artifacts from repository...
        </div>
      ) : filtered.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '4rem 1rem',
          backgroundColor: 'var(--bg-card)',
          borderRadius: '12px',
          border: '1px solid var(--border-default)',
          color: '#64748b'
        }}>
          <IconFileText size={40} color="#334155" style={{ marginBottom: '0.75rem' }} />
          <div style={{ fontSize: '1rem', color: '#94a3b8', fontWeight: 600 }}>No Deliverables Found</div>
          <div style={{ fontSize: '0.825rem', marginTop: '0.25rem' }}>
            Run Hero Flow 1 or launch a Document Task to generate branded DOCX, XLSX, PPTX, or PDF artifacts.
          </div>
        </div>
      ) : (
        <div className="grid-3col">
          {filtered.map((art) => (
            <ArtifactCard
              key={art.artifact_id}
              artifact={art}
              onViewSources={(a) => setSelectedArtifactForSources(a)}
            />
          ))}
        </div>
      )}

      {/* Sources Modal */}
      {selectedArtifactForSources && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'var(--bg-overlay)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1.5rem'
        }}>
          <div className="wb-card" style={{ maxWidth: '600px', width: '100%', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
            <div className="wb-card-header">
              <div className="wb-card-title">
                <IconLayers size={18} color="#38bdf8" />
                RAG Source Citations ({selectedArtifactForSources.title})
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                onClick={() => setSelectedArtifactForSources(null)}
              >
                Close
              </button>
            </div>

            <div style={{ overflowY: 'auto', flex: 1, padding: '0.5rem 0' }}>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                Knowledge base chunks and standards referenced during deliverable generation:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {selectedArtifactForSources.sources.map((src, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '0.6rem 0.85rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '6px',
                      fontSize: '0.775rem',
                      fontFamily: 'var(--font-mono)',
                      color: '#38bdf8'
                    }}
                  >
                    [{idx + 1}] {src}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};