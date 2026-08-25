import React from 'react';
import { Badge } from '../common/Badge';
import { IconDownload, IconFileText, IconLayers } from '../common/Icons';
import { api } from '../../services/api';
import type { ArtifactMeta } from '../../types';

interface ArtifactCardProps {
  artifact: ArtifactMeta;
  onViewSources: (artifact: ArtifactMeta) => void;
}

export const ArtifactCard: React.FC<ArtifactCardProps> = ({ artifact, onViewSources }) => {
  const getFormatBadge = (kind: string) => {
    switch (kind.toLowerCase()) {
      case 'docx':
        return <Badge variant="info">DOCX (Word)</Badge>;
      case 'xlsx':
        return <Badge variant="success">XLSX (Excel)</Badge>;
      case 'pptx':
        return <Badge variant="warning">PPTX (Deck)</Badge>;
      case 'pdf':
        return <Badge variant="error">PDF (Report)</Badge>;
      default:
        return <Badge variant="neutral">{kind.toUpperCase()}</Badge>;
    }
  };

  const createdTime = new Date(artifact.created_at).toLocaleString();

  return (
    <div className="wb-card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <IconFileText size={20} color="#38bdf8" />
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#f8fafc' }}>{artifact.title}</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
              ID: {artifact.artifact_id}
            </div>
          </div>
        </div>
        {getFormatBadge(artifact.kind)}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
        <span>Associated Task: <code style={{ color: '#38bdf8' }}>{artifact.task_id.substring(0, 10)}...</code></span>
        <span>{createdTime}</span>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
        <a
          href={api.getArtifactDownloadUrl(artifact.artifact_id)}
          className="btn btn-primary"
          style={{ flex: 1, fontSize: '0.775rem', padding: '0.45rem' }}
          download
        >
          <IconDownload size={14} />
          Download File
        </a>

        {artifact.sources && artifact.sources.length > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: '0.775rem', padding: '0.45rem 0.75rem' }}
            onClick={() => onViewSources(artifact)}
          >
            <IconLayers size={14} />
            Sources ({artifact.sources.length})
          </button>
        )}
      </div>
    </div>
  );
};