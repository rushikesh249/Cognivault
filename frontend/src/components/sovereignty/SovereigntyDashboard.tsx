import React from 'react';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { IconAlertTriangle, IconCheck, IconCpu, IconInfo, IconRefresh, IconShield } from '../common/Icons';
import { useSovereignty } from '../../hooks/useSovereignty';

export const SovereigntyDashboard: React.FC = () => {
  const { data, loading, error, refetch } = useSovereignty(5000);

  const getSubsystemBadge = (status?: string) => {
    if (status === 'ok') {
      return <Badge variant="success" icon={<IconCheck size={12} />}>OPERATIONAL</Badge>;
    }
    return <Badge variant="error" icon={<IconAlertTriangle size={12} />}>DEGRADED</Badge>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            Sovereignty & Air-Gap Security Monitor
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Live kernel socket inspection, egress detection, and local subsystem health guarantees.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={() => refetch()} disabled={loading}>
          <IconRefresh size={14} />
          Refresh Now
        </button>
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

      {/* 1. Outbound Cloud Egress Telemetry */}
      <div className="grid-3col">
        <Card title="External AI Calls" icon={<IconShield size={18} color="#10b981" />}>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: data?.external_ai_calls === 0 ? '#10b981' : '#ef4444' }}>
            {data?.external_ai_calls ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Outbound calls to external commercial AI providers
          </div>
        </Card>

        <Card title="External Embedding / OCR Calls" icon={<IconShield size={18} color="#10b981" />}>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: (data?.external_embedding_calls ?? 0) + (data?.external_ocr_calls ?? 0) === 0 ? '#10b981' : '#ef4444' }}>
            {(data?.external_embedding_calls ?? 0) + (data?.external_ocr_calls ?? 0)}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Cloud RAG embeddings & cloud vision API calls
          </div>
        </Card>

        <Card title="Data Egress (MB)" icon={<IconShield size={18} color="#10b981" />}>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: (data?.data_egress_mb ?? 0) === 0 ? '#10b981' : '#ef4444' }}>
            {(data?.data_egress_mb ?? 0).toFixed(2)} MB
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Total outbound network transmission detected
          </div>
        </Card>
      </div>

      {/* ADR-012 Byte Accounting Caveat */}
      {data && !data.byte_accounting_supported && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.8rem',
          color: '#cbd5e1'
        }}>
          <IconInfo size={20} color="#38bdf8" />
          <span>
            <strong>ADR-012 OS Adapter Notice:</strong> Byte-level hardware packet counting is not supported by the current host OS network adapter. Zero megabytes indicates zero established external socket connections rather than calibrated byte counting.
          </span>
        </div>
      )}

      {/* 2. Subsystems Health Grid */}
      <Card title="Local Subsystems Sovereignty Health Grid" icon={<IconCpu size={18} color="#38bdf8" />}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          <div style={{ padding: '0.85rem', backgroundColor: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Local LLM Inference</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Ollama Local Engine</div>
            </div>
            {getSubsystemBadge(data?.local_inference)}
          </div>

          <div style={{ padding: '0.85rem', backgroundColor: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Local OCR Engine</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>PaddleOCR / PyMuPDF</div>
            </div>
            {getSubsystemBadge(data?.local_ocr)}
          </div>

          <div style={{ padding: '0.85rem', backgroundColor: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Local RAG Vector DB</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>ChromaDB & ONNX</div>
            </div>
            {getSubsystemBadge(data?.local_rag)}
          </div>

          <div style={{ padding: '0.85rem', backgroundColor: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Local Vision Model</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Multimodal VLM</div>
            </div>
            {getSubsystemBadge(data?.local_vision)}
          </div>

          <div style={{ padding: '0.85rem', backgroundColor: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Docker Isolation Sandbox</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Ephemeral Container Runner</div>
            </div>
            {getSubsystemBadge(data?.local_sandbox)}
          </div>

          <div style={{ padding: '0.85rem', backgroundColor: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Sovereignty Monitor Thread</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Network Packet Sniffer</div>
            </div>
            {getSubsystemBadge(data?.monitor_status)}
          </div>
        </div>
      </Card>

      {/* 3. Rolling 5-Minute Telemetry */}
      <div className="grid-2col">
        <Card title="Rolling 5-Minute External Sockets" icon={<IconShield size={18} color="#38bdf8" />}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: data?.external_connections_5m === 0 ? '#10b981' : '#f59e0b' }}>
            {data?.external_connections_5m ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Unique non-loopback IP connections attempted in past 300 seconds.
          </div>
        </Card>

        <Card title="Rolling 5-Minute DNS Lookups" icon={<IconShield size={18} color="#38bdf8" />}>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: data?.external_dns_lookups_5m === 0 ? '#10b981' : '#f59e0b' }}>
            {data?.external_dns_lookups_5m ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            External domain name resolution queries logged in past 300 seconds.
          </div>
        </Card>
      </div>
    </div>
  );
};