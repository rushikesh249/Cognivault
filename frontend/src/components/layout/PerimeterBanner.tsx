import React from 'react';
import { IconLock, IconServer } from '../common/Icons';
import type { SovereigntyStatus } from '../../types';

interface PerimeterBannerProps {
  sovereignty: SovereigntyStatus | null;
}

export const PerimeterBanner: React.FC<PerimeterBannerProps> = ({ sovereignty }) => {
  const isZeroEgress = sovereignty?.external_ai_calls === 0 && (sovereignty?.data_egress_mb ?? 0) === 0;

  return (
    <div className="cv-perimeter-banner">
      {/* 1. Network Isolation Status */}
      <div className="cv-perimeter-item">
        <span className={`cv-status-dot ${isZeroEgress ? 'green' : 'red'}`} />
        <span className="cv-perimeter-text">
          <strong style={{ color: '#111827' }}>Network Isolation:</strong>{' '}
          {isZeroEgress ? 'Level 4 (Fully Isolated)' : 'Egress Detected'}
        </span>
      </div>

      <div className="cv-perimeter-divider" />

      {/* 2. Encryption Guarantee */}
      <div className="cv-perimeter-item">
        <IconLock size={15} color="#4b5563" />
        <span className="cv-perimeter-text">
          <strong style={{ color: '#111827' }}>Encryption:</strong> AES-256-GCM
        </span>
      </div>

      <div className="cv-perimeter-divider" />

      {/* 3. On-Premise Node Reference */}
      <div className="cv-perimeter-item">
        <IconServer size={15} color="#4b5563" />
        <span className="cv-perimeter-text">
          <strong style={{ color: '#111827' }}>On-Premise Node:</strong> US-EAST-SEC-01
        </span>
      </div>
    </div>
  );
};
