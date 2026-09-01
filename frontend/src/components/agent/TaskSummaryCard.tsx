import React from 'react';
import { Badge } from '../common/Badge';
import {
  IconCheck,
  IconDownload,
  IconFileText,
  IconInfo,
} from '../common/Icons';
import { api } from '../../services/api';
import type { TaskDetail, TaskStatus } from '../../types';

interface TaskSummaryCardProps {
  task: TaskDetail | null;
  finalStatus: TaskStatus | null;
  onViewArtifacts?: () => void;
}

export const TaskSummaryCard: React.FC<TaskSummaryCardProps> = ({
  task,
  finalStatus,
  onViewArtifacts,
}) => {
  if (!task) return null;

  const currentStatus = finalStatus || task.status;

  let badgeVariant: 'success' | 'warning' | 'error' | 'info' = 'info';
  if (currentStatus === 'succeeded') badgeVariant = 'success';
  else if (currentStatus === 'failed_bounded') badgeVariant = 'warning';
  else if (currentStatus === 'failed') badgeVariant = 'error';

  return (
    <div className="cv-card cv-task-active-card">
      <div className="cv-card-header-row">
        <div className="cv-card-title-group">
          <IconInfo size={16} color="#19a7d8" />
          <h3 className="cv-card-heading">Active Task Run</h3>
        </div>
        <Badge variant={badgeVariant}>
          {currentStatus.toUpperCase()}
        </Badge>
      </div>

      <div className="cv-task-meta-grid">
        <div className="cv-meta-item">
          <span className="cv-meta-key">TASK ID</span>
          <span className="cv-meta-val cv-mono-val">{task.task_id}</span>
        </div>

        <div className="cv-meta-item">
          <span className="cv-meta-key">TITLE</span>
          <span className="cv-meta-val">{task.title}</span>
        </div>

        <div className="cv-meta-item">
          <span className="cv-meta-key">CATEGORY</span>
          <span className="cv-meta-val" style={{ textTransform: 'capitalize' }}>
            {task.task_type}
          </span>
        </div>

        <div className="cv-meta-item">
          <span className="cv-meta-key">MODEL SELECTED</span>
          <span className="cv-meta-val cv-model-highlight">
            {task.model_used || 'Autonomous Routing...'}
          </span>
        </div>
      </div>

      {task.artifact_ids && task.artifact_ids.length > 0 && (
        <div className="cv-task-deliverables-section">
          <div className="cv-deliverables-header">
            <span className="cv-deliverables-title">
              <IconCheck size={14} color="#22c55e" />
              Generated Deliverables ({task.artifact_ids.length}):
            </span>
            {onViewArtifacts && (
              <button
                type="button"
                className="cv-btn-mini-link"
                onClick={onViewArtifacts}
              >
                <IconFileText size={12} />
                <span>View in Catalog</span>
              </button>
            )}
          </div>
          <div className="cv-deliverables-buttons">
            {task.artifact_ids.map((artId) => (
              <a
                key={artId}
                href={api.getArtifactDownloadUrl(artId)}
                className="cv-btn-deliverable-download"
                download
              >
                <IconDownload size={13} />
                <span>Download ({artId.substring(0, 8)}...)</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};