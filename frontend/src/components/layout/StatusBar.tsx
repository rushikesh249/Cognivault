import React from 'react';
import type { SovereigntyStatus } from '../../types';

interface StatusBarProps {
  sovereignty: SovereigntyStatus | null;
  activeModel?: string | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({ sovereignty, activeModel }) => {
  return (
    <footer className="wb-statusbar">
      <div className="wb-status-item">
        <span style={{ color: '#64748b' }}>EXTERNAL_AI_CALLS:</span>
        <span style={{ color: sovereignty?.external_ai_calls === 0 ? '#10b981' : '#ef4444' }}>
          {sovereignty?.external_ai_calls ?? 0}
        </span>
      </div>

      <div className="wb-status-item">
        <span style={{ color: '#64748b' }}>EGRESS_MB:</span>
        <span style={{ color: (sovereignty?.data_egress_mb ?? 0) === 0 ? '#10b981' : '#ef4444' }}>
          {(sovereignty?.data_egress_mb ?? 0).toFixed(2)} MB
        </span>
      </div>

      <div className="wb-status-item">
        <span style={{ color: '#64748b' }}>5M_EXT_CONN:</span>
        <span>{sovereignty?.external_connections_5m ?? 0}</span>
      </div>

      <div className="wb-status-item">
        <span style={{ color: '#64748b' }}>MONITOR_STATUS:</span>
        <span style={{ color: sovereignty?.monitor_status === 'ok' ? '#10b981' : '#f59e0b' }}>
          {(sovereignty?.monitor_status ?? 'UNKNOWN').toUpperCase()}
        </span>
      </div>

      <div className="wb-status-item">
        <span style={{ color: '#64748b' }}>MODEL:</span>
        <span style={{ color: '#38bdf8' }}>{activeModel || 'auto-routing'}</span>
      </div>
    </footer>
  );
};