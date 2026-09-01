import React from 'react';
import { Badge } from '../common/Badge';
import {
  IconAlertTriangle,
  IconCheck,
  IconCpu,
  IconDatabase,
  IconLock,
  IconRefresh,
  IconServer,
  IconShield,
} from '../common/Icons';
import { useSovereignty } from '../../hooks/useSovereignty';

export const SovereigntyDashboard: React.FC = () => {
  const { data, loading, error, refetch } = useSovereignty(5000);

  const getSubsystemBadge = (status?: string) => {
    if (status === 'ok') {
      return <Badge variant="success" icon={<IconCheck size={13} />}>OPERATIONAL</Badge>;
    }
    return <Badge variant="error" icon={<IconAlertTriangle size={13} />}>DEGRADED</Badge>;
  };

  return (
    <div className="cv-view-layout">
      {/* Top Header Row */}
      <div className="cv-section-header-row">
        <div>
          <h2 className="cv-section-title">Sovereignty & Air-Gap Security Monitor</h2>
          <p className="cv-section-subtitle">
            Live socket inspection, kernel egress detection, and local subsystem health guarantees.
          </p>
        </div>

        <button
          type="button"
          className="cv-btn-compact-secondary"
          onClick={() => refetch()}
          disabled={loading}
        >
          <IconRefresh size={15} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {error && (
        <div className="cv-form-error-banner">
          {error} (Telemetry unavailable, preserving local perimeter state)
        </div>
      )}

      {/* 1. Outbound Cloud Egress Telemetry Cards */}
      <div className="cv-3col-metrics-grid">
        <div className="cv-card cv-metric-card">
          <div className="cv-metric-label-row">
            <span className="cv-metric-label">EXTERNAL AI CALLS</span>
            <IconShield size={18} color={data?.external_ai_calls === 0 ? '#15803d' : '#b91c1c'} />
          </div>
          <div className={`cv-metric-large-val ${data?.external_ai_calls === 0 ? 'cv-text-green' : 'cv-text-red'}`}>
            {data?.external_ai_calls ?? 0}
          </div>
          <div className="cv-metric-subtext">
            Outbound requests to external commercial AI providers
          </div>
        </div>

        <div className="cv-card cv-metric-card">
          <div className="cv-metric-label-row">
            <span className="cv-metric-label">EXTERNAL EMBEDDING / OCR</span>
            <IconShield size={18} color={(data?.external_embedding_calls ?? 0) + (data?.external_ocr_calls ?? 0) === 0 ? '#15803d' : '#b91c1c'} />
          </div>
          <div className={`cv-metric-large-val ${(data?.external_embedding_calls ?? 0) + (data?.external_ocr_calls ?? 0) === 0 ? 'cv-text-green' : 'cv-text-red'}`}>
            {(data?.external_embedding_calls ?? 0) + (data?.external_ocr_calls ?? 0)}
          </div>
          <div className="cv-metric-subtext">
            Third-party cloud embeddings or vision API calls
          </div>
        </div>

        <div className="cv-card cv-metric-card">
          <div className="cv-metric-label-row">
            <span className="cv-metric-label">DATA EGRESS (MB)</span>
            <IconShield size={18} color={(data?.data_egress_mb ?? 0) === 0 ? '#15803d' : '#b91c1c'} />
          </div>
          <div className={`cv-metric-large-val ${(data?.data_egress_mb ?? 0) === 0 ? 'cv-text-green' : 'cv-text-red'}`}>
            {(data?.data_egress_mb ?? 0).toFixed(2)} MB
          </div>
          <div className="cv-metric-subtext">
            Total outbound network transmission detected
          </div>
        </div>
      </div>

      {/* 2. Subsystem Isolation & Health Status Grid */}
      <div className="cv-card cv-subsystems-card">
        <h3 className="cv-card-heading" style={{ marginBottom: '1.1rem' }}>
          On-Premise Isolated Subsystems
        </h3>

        <div className="cv-subsystems-table-wrap">
          <table className="cv-data-table">
            <thead>
              <tr>
                <th>SUBSYSTEM</th>
                <th>ROLE</th>
                <th>ISOLATION LEVEL</th>
                <th style={{ textAlign: 'right' }}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <div className="cv-subsystem-name">
                    <IconCpu size={17} color="#4338ca" />
                    <strong style={{ color: '#111827' }}>Local Inference (Ollama)</strong>
                  </div>
                </td>
                <td>Autonomous Reasoning & Decision Loop</td>
                <td>
                  <span className="cv-badge-isolation">Air-Gapped Local</span>
                </td>
                <td style={{ textAlign: 'right' }}>{getSubsystemBadge(data?.local_inference)}</td>
              </tr>

              <tr>
                <td>
                  <div className="cv-subsystem-name">
                    <IconDatabase size={17} color="#4338ca" />
                    <strong style={{ color: '#111827' }}>Local RAG Engine (ChromaDB)</strong>
                  </div>
                </td>
                <td>Knowledge Base Vector Embeddings</td>
                <td>
                  <span className="cv-badge-isolation">Air-Gapped Local</span>
                </td>
                <td style={{ textAlign: 'right' }}>{getSubsystemBadge(data?.local_rag)}</td>
              </tr>

              <tr>
                <td>
                  <div className="cv-subsystem-name">
                    <IconShield size={17} color="#4338ca" />
                    <strong style={{ color: '#111827' }}>Local OCR (Tesseract / EasyOCR)</strong>
                  </div>
                </td>
                <td>On-Premise Document Text Extraction</td>
                <td>
                  <span className="cv-badge-isolation">Air-Gapped Local</span>
                </td>
                <td style={{ textAlign: 'right' }}>{getSubsystemBadge(data?.local_ocr)}</td>
              </tr>

              <tr>
                <td>
                  <div className="cv-subsystem-name">
                    <IconServer size={17} color="#4338ca" />
                    <strong style={{ color: '#111827' }}>Local Docker Sandbox</strong>
                  </div>
                </td>
                <td>Restricted Code Execution & Testing</td>
                <td>
                  <span className="cv-badge-isolation">Isolated Container</span>
                </td>
                <td style={{ textAlign: 'right' }}>{getSubsystemBadge(data?.local_sandbox)}</td>
              </tr>

              <tr>
                <td>
                  <div className="cv-subsystem-name">
                    <IconLock size={17} color="#4338ca" />
                    <strong style={{ color: '#111827' }}>Kernel Security Monitor</strong>
                  </div>
                </td>
                <td>Socket Egress & Packet Audit</td>
                <td>
                  <span className="cv-badge-isolation">Host Level</span>
                </td>
                <td style={{ textAlign: 'right' }}>{getSubsystemBadge(data?.monitor_status)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};