import React from 'react';
import { Badge } from '../common/Badge';
import { IconCpu, IconShield } from '../common/Icons';
import type { SovereigntyStatus } from '../../types';

interface HeaderProps {
  sovereignty: SovereigntyStatus | null;
}

export const Header: React.FC<HeaderProps> = ({ sovereignty }) => {
  const isEgressZero = sovereignty?.data_egress_mb === 0 && sovereignty.external_ai_calls === 0;

  return (
    <header className="wb-header">
      <div className="wb-brand">
        <IconShield size={24} color="#38bdf8" />
        <div>
          <div className="wb-brand-title">
            Cognivault
            <span style={{ fontSize: '0.8rem', fontWeight: 400, color: '#94a3b8' }}>v1.0-Sovereign</span>
          </div>
          <div className="wb-brand-subtitle">Sovereign On-Premise Agentic AI Workbench</div>
        </div>
      </div>

      <div className="wb-header-meta">
        <Badge variant={isEgressZero ? 'success' : 'warning'} icon={<IconShield size={12} />}>
          {isEgressZero ? 'AIR-GAPPED / ZERO EGRESS' : 'EGRESS DETECTED'}
        </Badge>
        <Badge
          variant={sovereignty?.local_inference === 'ok' ? 'success' : 'error'}
          icon={<IconCpu size={12} />}
        >
          {sovereignty?.local_inference === 'ok' ? 'LOCAL OLLAMA: ONLINE' : 'LOCAL OLLAMA: DEGRADED'}
        </Badge>
      </div>
    </header>
  );
};