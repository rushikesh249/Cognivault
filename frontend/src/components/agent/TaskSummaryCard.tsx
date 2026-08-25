import React from 'react';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { IconCheck, IconDownload, IconFileText, IconInfo } from '../common/Icons';
import { api } from '../../services/api';
import type { TaskDetail, TaskStatus } from '../../types';

interface TaskSummaryCardProps {
  task: TaskDetail | null;
  finalStatus: TaskStatus | null;
  onViewArtifacts?: () => void;
}

export const TaskSummaryCard: React.FC<TaskSummaryCardProps> = ({ task, finalStatus, onViewArtifacts }) => {
  if (!task) return null;

  const currentStatus = finalStatus || task.status;

  return (
    <Card
      title="Active Task Information"
      icon={<IconInfo size={18} color="#38bdf8" />}
      badge={
        <Badge
          variant={
            currentStatus === 'succeeded'
              ? 'success'
              : currentStatus === 'failed_bounded'
              ? 'warning'
              : currentStatus === 'failed'
              ? 'error'
              : 'info'
          }
        >
          {currentStatus.toUpperCase()}
        </Badge>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.825rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.4rem' }}>
          <span style={{ color: '#64748b' }}>Task ID:</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{task.task_id}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.4rem' }}>
          <span style={{ color: '#64748b' }}>Title:</span>
          <span style={{ fontWeight: 600 }}>{task.title}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.4rem' }}>
          <span style={{ color: '#64748b' }}>Type:</span>
          <span style={{ textTransform: 'capitalize' }}>{task.task_type}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.4rem' }}>
          <span style={{ color: '#64748b' }}>Model Selected:</span>
          <span style={{ color: '#38bdf8' }}>{task.model_used || 'Routing dynamically...'}</span>
        </div>

        {task.artifact_ids && task.artifact_ids.length > 0 && (
          <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <IconCheck size={14} /> Deliverables Generated ({task.artifact_ids.length}):
              </span>
              {onViewArtifacts && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                  onClick={onViewArtifacts}
                >
                  <IconFileText size={12} />
                  View in Catalog
                </button>
              )}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {task.artifact_ids.map((artId) => (
                <a
                  key={artId}
                  href={api.getArtifactDownloadUrl(artId)}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                  download
                >
                  <IconDownload size={13} />
                  Download ({artId.substring(0, 8)}...)
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};