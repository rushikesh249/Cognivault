import React from 'react';
import { Badge } from '../common/Badge';
import { IconCompass, IconCpu, IconRefresh } from '../common/Icons';
import { useModels } from '../../hooks/useModels';

export const ModelsView: React.FC = () => {
  const { models, loading, error, refetch } = useModels();

  return (
    <div className="cv-view-layout">
      <div className="cv-section-header-row">
        <div>
          <h2 className="cv-section-title">Sovereign Model Registry</h2>
          <p className="cv-section-subtitle">
            Local Ollama LLM / VLM instances deployed within the air-gapped on-premise perimeter.
          </p>
        </div>

        <button
          type="button"
          className="cv-btn-compact-secondary"
          onClick={() => refetch()}
          disabled={loading}
        >
          <IconRefresh size={15} />
          <span>Refresh Models</span>
        </button>
      </div>

      {error && <div className="cv-form-error-banner">{error}</div>}

      {loading ? (
        <div className="cv-loading-center" style={{ textAlign: 'center', padding: '3rem', fontSize: '0.9rem', color: '#6b7280' }}>
          Loading model status from local Ollama...
        </div>
      ) : models.length === 0 ? (
        <div className="cv-empty-state-table cv-card">
          <IconCompass size={40} color="#9ca3af" />
          <div className="cv-empty-title">No Local Models Detected</div>
          <div className="cv-empty-desc">
            Ensure the local Ollama backend is running and models (Llama 3, Qwen 2.5, LLaVA) are loaded.
          </div>
        </div>
      ) : (
        <div className="cv-card cv-table-card">
          <table className="cv-data-table">
            <thead>
              <tr>
                <th>MODEL</th>
                <th>ROLE</th>
                <th>BACKEND</th>
                <th>CONTEXT</th>
                <th>VRAM</th>
                <th style={{ textAlign: 'right' }}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.model_id}>
                  <td>
                    <div className="cv-subsystem-name">
                      <IconCpu size={17} color="#4338ca" />
                      <strong style={{ color: '#111827' }}>{m.display_name || m.model_id}</strong>
                    </div>
                  </td>
                  <td>
                    <span className="cv-badge-isolation">{m.role}</span>
                  </td>
                  <td>
                    <span className="cv-mono-text">{m.serving_backend}</span>
                  </td>
                  <td>
                    <span className="cv-mono-text">{m.context_length ? `${(m.context_length / 1024).toFixed(0)}k` : '8k'}</span>
                  </td>
                  <td>
                    <span className="cv-mono-text">{m.vram_gb ? `${m.vram_gb} GB` : 'Auto'}</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Badge variant={m.available ? 'success' : 'warning'}>
                      {m.available ? 'AVAILABLE' : 'OFFLINE'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
