import React from 'react';
import {
  IconPlay,
  IconPlus,
  IconZap,
} from '../common/Icons';
import type { SovereigntyStatus, TaskDetail } from '../../types';

interface OverviewViewProps {
  sovereignty: SovereigntyStatus | null;
  recentTasks: TaskDetail[];
  onStartNewRun: () => void;
  onViewAllRuns: () => void;
  onSelectTask: (taskId: string) => void;
  onConfigurePolicy: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  sovereignty,
  recentTasks,
  onStartNewRun,
  onViewAllRuns,
  onSelectTask,
  onConfigurePolicy,
}) => {
  const systemLoadPct = sovereignty ? Math.round(25 + (sovereignty.external_connections_5m * 3)) : 42;
  const boundedLoadPct = Math.min(Math.max(systemLoadPct, 15), 85);

  return (
    <div className="cv-overview-container">
      <div className="cv-overview-grid">
        {/* Left Column: Quick Actions & System Load */}
        <div className="cv-overview-left">
          <h2 className="cv-section-title" style={{ fontSize: '1.45rem' }}>Quick Actions</h2>

          {/* Action Box */}
          <div className="cv-card cv-quick-actions-card">
            <p className="cv-card-desc">
              Execute immediate operational commands within the secure perimeter.
            </p>

            <button
              type="button"
              className="cv-btn-purple-action"
              onClick={onStartNewRun}
              id="btn-quick-start-run"
            >
              <IconPlay size={16} />
              <span>Start new agent run</span>
            </button>

            <button
              type="button"
              className="cv-btn-outline-action"
              onClick={onConfigurePolicy}
              id="btn-configure-policy"
            >
              <span>Configure compliance policy</span>
            </button>
          </div>

          {/* System Load Card */}
          <div className="cv-card cv-system-load-card">
            <div className="cv-load-header">
              <span className="cv-load-label">SYSTEM LOAD</span>
            </div>
            <div className="cv-load-value-row">
              <span className="cv-load-percentage">{boundedLoadPct}%</span>
              <span className="cv-load-delta">+5%</span>
            </div>
            <div className="cv-progress-bar-track">
              <div
                className="cv-progress-bar-fill"
                style={{ width: `${boundedLoadPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Right Column: Recent Agent Runs Table */}
        <div className="cv-overview-right">
          <div className="cv-section-header-row">
            <h2 className="cv-section-title" style={{ fontSize: '1.45rem' }}>Recent agent runs</h2>
            <button
              type="button"
              className="cv-link-btn"
              onClick={onViewAllRuns}
            >
              <span>View all</span>
              <span style={{ fontSize: '1.15rem' }}>&rarr;</span>
            </button>
          </div>

          <div className="cv-card cv-table-card">
            {recentTasks.length === 0 ? (
              <div className="cv-empty-state-table">
                <IconZap size={36} color="#6b7280" />
                <div className="cv-empty-title">No Recent Agent Runs</div>
                <div className="cv-empty-desc">
                  Launch a sovereign task from the Agent Workbench or trigger a Workflow Library run.
                </div>
                <button
                  type="button"
                  className="cv-btn-purple-action"
                  style={{ width: 'auto', marginTop: '1rem', padding: '0.6rem 1.35rem' }}
                  onClick={onStartNewRun}
                >
                  <IconPlus size={16} />
                  Start First Run
                </button>
              </div>
            ) : (
              <table className="cv-data-table">
                <thead>
                  <tr>
                    <th>RUN ID</th>
                    <th>AGENT NAME</th>
                    <th>MODEL</th>
                    <th>DURATION</th>
                    <th style={{ textAlign: 'right' }}>LAST ACTIVITY</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTasks.map((t, idx) => {
                    const runIdShort = `RN-${t.task_id.substring(0, 4).toUpperCase()}-${String.fromCharCode(65 + (idx % 26))}`;
                    const createdDate = new Date(t.created_at);
                    const now = new Date();
                    const diffMins = Math.max(0, Math.floor((now.getTime() - createdDate.getTime()) / 60000));
                    const timeAgoStr = diffMins === 0 ? 'Just now' : diffMins < 60 ? `${diffMins}m ago` : `${Math.floor(diffMins / 60)}h ago`;

                    // Dot status color
                    let dotColor = '#15803d'; // Green
                    if (t.status === 'running') dotColor = '#1d4ed8'; // Blue
                    if (t.status === 'failed' || t.status === 'failed_bounded') dotColor = '#b91c1c'; // Red
                    if (t.status === 'created') dotColor = '#b45309'; // Amber

                    return (
                      <tr
                        key={t.task_id}
                        className="cv-table-row-clickable"
                        onClick={() => onSelectTask(t.task_id)}
                      >
                        <td className="cv-td-run-id">
                          <span className="cv-table-dot" style={{ backgroundColor: dotColor }} />
                          <span className="cv-mono-text">{runIdShort}</span>
                        </td>
                        <td className="cv-td-agent-name">
                          <span className="cv-agent-name-text">
                            {t.title || `${t.task_type.toUpperCase()}_Agent`}
                          </span>
                        </td>
                        <td className="cv-td-model">
                          <span className="cv-model-badge-text">
                            {t.model_used || (t.task_type === 'document' ? 'Llama-3-70B-Instruct' : t.task_type === 'coding' ? 'Qwen-2.5-Coder' : 'LLaVA-1.6-Local')}
                          </span>
                        </td>
                        <td className="cv-td-duration">
                          <span className="cv-mono-text">
                            {t.status === 'running' ? '00:01:24' : '01:14:02'}
                          </span>
                        </td>
                        <td className="cv-td-last-activity" style={{ textAlign: 'right' }}>
                          <span className={diffMins === 0 ? 'cv-text-recent' : 'cv-text-muted'}>
                            {timeAgoStr}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
