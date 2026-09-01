import React, { useState } from 'react';
import { ArtifactCard } from './ArtifactCard';
import { IconFileText, IconLayers, IconRefresh, IconSearch } from '../common/Icons';
import { useArtifacts } from '../../hooks/useArtifacts';
import type { ArtifactMeta } from '../../types';

export const ArtifactExplorer: React.FC = () => {
  const { artifacts, loading, error, refetch } = useArtifacts();
  const [selectedFormat, setSelectedFormat] = useState<string>('all');
  const [selectedArtifactForSources, setSelectedArtifactForSources] = useState<ArtifactMeta | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filtered = artifacts.filter((art) => {
    const matchesFormat = selectedFormat === 'all' || art.kind.toLowerCase() === selectedFormat.toLowerCase();
    const matchesSearch = !searchQuery.trim() ||
      art.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      art.artifact_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFormat && matchesSearch;
  });

  return (
    <div className="cv-view-layout">
      <div className="cv-section-header-row">
        <div>
          <h2 className="cv-section-title">Deliverables & RAG Knowledge Catalog</h2>
          <p className="cv-section-subtitle">
            Browse, inspect source citations, and download multi-format deliverables (DOCX, XLSX, PPTX, PDF).
          </p>
        </div>

        <div className="cv-filter-actions-row">
          <div className="cv-search-mini-wrap">
            <IconSearch size={15} color="#4b5563" />
            <input
              type="text"
              className="cv-search-mini-input"
              placeholder="Search deliverables..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="cv-select-compact"
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
          >
            <option value="all">All Formats ({artifacts.length})</option>
            <option value="docx">DOCX Word</option>
            <option value="xlsx">XLSX Excel</option>
            <option value="pptx">PPTX Deck</option>
            <option value="pdf">PDF Report</option>
          </select>

          <button
            type="button"
            className="cv-btn-compact-secondary"
            onClick={() => refetch()}
            disabled={loading}
          >
            <IconRefresh size={15} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && <div className="cv-form-error-banner">{error}</div>}

      {loading ? (
        <div className="cv-loading-center" style={{ textAlign: 'center', padding: '3rem', fontSize: '0.9rem', color: '#6b7280' }}>
          Loading deliverables from secure repository...
        </div>
      ) : filtered.length === 0 ? (
        <div className="cv-empty-state-table cv-card">
          <IconFileText size={40} color="#9ca3af" />
          <div className="cv-empty-title">No Deliverables Found</div>
          <div className="cv-empty-desc">
            Launch a sovereign document or analysis run to generate verified multi-format artifacts.
          </div>
        </div>
      ) : (
        <div className="cv-3col-cards-grid">
          {filtered.map((art) => (
            <ArtifactCard
              key={art.artifact_id}
              artifact={art}
              onViewSources={(a) => setSelectedArtifactForSources(a)}
            />
          ))}
        </div>
      )}

      {/* Sources Citations Modal */}
      {selectedArtifactForSources && (
        <div className="cv-modal-backdrop" onClick={() => setSelectedArtifactForSources(null)}>
          <div className="cv-modal-box cv-card" onClick={(e) => e.stopPropagation()}>
            <div className="cv-card-header-row">
              <div className="cv-card-title-group">
                <IconLayers size={18} color="#4338ca" />
                <h3 className="cv-card-heading">
                  RAG Source Citations ({selectedArtifactForSources.title})
                </h3>
              </div>
              <button
                type="button"
                className="cv-btn-compact-secondary"
                onClick={() => setSelectedArtifactForSources(null)}
              >
                Close
              </button>
            </div>

            <div className="cv-modal-body">
              <p className="cv-modal-body-subtext">
                Knowledge base chunks and regulatory standards referenced during autonomous generation:
              </p>
              <div className="cv-citations-list">
                {selectedArtifactForSources.sources.map((src, idx) => (
                  <div key={idx} className="cv-citation-card">
                    <span className="cv-citation-idx">[{idx + 1}]</span>
                    <span className="cv-citation-content">{src}</span>
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