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
        return <Badge variant="info">DOCX</Badge>;
      case 'xlsx':
        return <Badge variant="success">XLSX</Badge>;
      case 'pptx':
        return <Badge variant="warning">PPTX</Badge>;
      case 'pdf':
        return <Badge variant="error">PDF</Badge>;
      default:
        return <Badge variant="neutral">{kind.toUpperCase()}</Badge>;
    }
  };

  const createdTime = new Date(artifact.created_at).toLocaleString();

  return (
    <div className="cv-card cv-artifact-item-card">
      <div className="cv-artifact-top-row">
        <div className="cv-artifact-title-group">
          <div className="cv-artifact-icon-wrap">
            <IconFileText size={18} color="#4338ca" />
          </div>
          <div>
            <div className="cv-artifact-title">{artifact.title}</div>
            <div className="cv-artifact-id-mono">{artifact.artifact_id}</div>
          </div>
        </div>
        {getFormatBadge(artifact.kind)}
      </div>

      <div className="cv-artifact-meta-line">
        <span>Task: <code className="cv-code-snippet">{artifact.task_id.substring(0, 8)}...</code></span>
        <span>{createdTime}</span>
      </div>

      <div className="cv-artifact-actions-row">
        <a
          href={api.getArtifactDownloadUrl(artifact.artifact_id)}
          className="cv-btn-purple-action"
          style={{ flex: 1, padding: '0.45rem 0.85rem', fontSize: '0.825rem' }}
          download
        >
          <IconDownload size={14} />
          <span>Download</span>
        </a>

        {artifact.sources && artifact.sources.length > 0 && (
          <button
            type="button"
            className="cv-btn-compact-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.825rem' }}
            onClick={() => onViewSources(artifact)}
          >
            <IconLayers size={14} />
            <span>Sources ({artifact.sources.length})</span>
          </button>
        )}
      </div>
    </div>
  );
};