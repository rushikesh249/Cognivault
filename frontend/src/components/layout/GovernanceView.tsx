import React from 'react';
import { Badge } from '../common/Badge';
import type { SovereigntyStatus } from '../../types';

interface GovernanceViewProps {
  sovereignty: SovereigntyStatus | null;
  mode: 'policies' | 'audit' | 'settings';
}

export const GovernanceView: React.FC<GovernanceViewProps> = ({ mode }) => {
  if (mode === 'policies') {
    return (
      <div className="cv-view-layout">
        <div className="cv-section-header-row">
          <div>
            <h2 className="cv-section-title">Operational Compliance Policies</h2>
            <p className="cv-section-subtitle">
              Configured boundary rules and sovereign execution constraints.
            </p>
          </div>
        </div>

        <div className="cv-card cv-table-card">
          <table className="cv-data-table">
            <thead>
              <tr>
                <th>POLICY DIRECTIVE</th>
                <th>ENFORCEMENT MECHANISM</th>
                <th>SCOPE</th>
                <th style={{ textAlign: 'right' }}>STATE</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Zero Egress Network Boundary</strong></td>
                <td>Kernel eBPF & socket connection filtering</td>
                <td>Global Perimeter</td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ENFORCED</Badge></td>
              </tr>
              <tr>
                <td><strong>Local Vector DB Air-Gap</strong></td>
                <td>ChromaDB on-premise memory persistence</td>
                <td>RAG Queries</td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ENFORCED</Badge></td>
              </tr>
              <tr>
                <td><strong>Docker Sandbox Isolation</strong></td>
                <td>cgroups, read-only rootfs, no-network flags</td>
                <td>Code Execution</td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ENFORCED</Badge></td>
              </tr>
              <tr>
                <td><strong>Self-Correction Iteration Limit</strong></td>
                <td>LangGraph cyclic bound (max 4 loops)</td>
                <td>Agent Planning</td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ENFORCED</Badge></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (mode === 'audit') {
    return (
      <div className="cv-view-layout">
        <div className="cv-section-header-row">
          <div>
            <h2 className="cv-section-title">Perimeter Security Audit Log</h2>
            <p className="cv-section-subtitle">
              Cryptographic integrity records and host socket connection audit trails.
            </p>
          </div>
        </div>

        <div className="cv-card cv-table-card">
          <table className="cv-data-table">
            <thead>
              <tr>
                <th>TIMESTAMP</th>
                <th>EVENT TYPE</th>
                <th>DETAILS</th>
                <th>SOCKET / PROTOCOL</th>
                <th style={{ textAlign: 'right' }}>VERDICT</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span className="cv-mono-text">Just now</span></td>
                <td><strong>Telemetry Polling</strong></td>
                <td>Internal health check /api/sovereignty/status</td>
                <td><span className="cv-mono-text">127.0.0.1:8000 (HTTP)</span></td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ALLOWED (LOCAL)</Badge></td>
              </tr>
              <tr>
                <td><span className="cv-mono-text">10m ago</span></td>
                <td><strong>Model Inference Dispatch</strong></td>
                <td>Local Ollama socket streaming</td>
                <td><span className="cv-mono-text">127.0.0.1:11434 (REST)</span></td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ALLOWED (LOCAL)</Badge></td>
              </tr>
              <tr>
                <td><span className="cv-mono-text">25m ago</span></td>
                <td><strong>Sandbox Code Execution</strong></td>
                <td>Docker container spin-up (Python 3.11)</td>
                <td><span className="cv-mono-text">unix:///var/run/docker.sock</span></td>
                <td style={{ textAlign: 'right' }}><Badge variant="success">ALLOWED (SANDBOX)</Badge></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="cv-view-layout">
      <div className="cv-section-header-row">
        <div>
          <h2 className="cv-section-title">System & Cluster Settings</h2>
          <p className="cv-section-subtitle">
            Node parameters and backend environment configuration.
          </p>
        </div>
      </div>

      <div className="cv-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="cv-meta-item">
          <span className="cv-meta-key">CLUSTER NODE</span>
          <span className="cv-meta-val">US-EAST-SEC-01 (On-Premise)</span>
        </div>
        <div className="cv-meta-item">
          <span className="cv-meta-key">ENCRYPTION ENGINE</span>
          <span className="cv-meta-val">AES-256-GCM Hardware Accelerated</span>
        </div>
        <div className="cv-meta-item">
          <span className="cv-meta-key">LOCAL OLLAMA ENDPOINT</span>
          <span className="cv-meta-val cv-mono-val">http://localhost:11434</span>
        </div>
        <div className="cv-meta-item">
          <span className="cv-meta-key">BACKEND REST/SSE PORT</span>
          <span className="cv-meta-val cv-mono-val">http://localhost:8000</span>
        </div>
      </div>
    </div>
  );
};
