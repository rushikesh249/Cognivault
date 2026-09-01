import React from 'react';
import { IconCheck } from '../common/Icons';
import type { LangGraphNode, SovereigntyStatus, TaskStatus } from '../../types';

interface WorkbenchSidePanelsProps {
  activeNode: LangGraphNode | null;
  completedNodes: LangGraphNode[];
  finalStatus: TaskStatus | null;
  sovereignty: SovereigntyStatus | null;
  isStreaming?: boolean;
}

interface StageItem {
  key: LangGraphNode;
  label: string;
}

const STAGES: StageItem[] = [
  { key: 'task_understanding', label: 'Task Understanding' },
  { key: 'planning', label: 'Planning' },
  { key: 'model_selection', label: 'Model Selection' },
  { key: 'tool_selection', label: 'Tool Selection' },
  { key: 'execution', label: 'Tool Execution' },
  { key: 'observation', label: 'Observation' },
  { key: 'validation', label: 'Validation' },
  { key: 'final_deliverable', label: 'Final Deliverable' },
];

export const WorkbenchSidePanels: React.FC<WorkbenchSidePanelsProps> = ({
  activeNode,
  completedNodes,
  finalStatus,
  sovereignty,
}) => {
  const isZeroEgress = sovereignty?.external_ai_calls === 0 && (sovereignty?.data_egress_mb ?? 0) === 0;

  return (
    <div className="cv-workbench-side-panels">
      {/* 1. Execution Preview Card */}
      <div className="cv-card cv-preview-card">
        <h3 className="cv-side-panel-title">Execution preview</h3>
        <div className="cv-stage-steps-list">
          {STAGES.map((stg, idx) => {
            const isFinalDeliverable = stg.key === 'final_deliverable';
            const isTerminal = isFinalDeliverable && finalStatus !== null;
            const isActive = activeNode === stg.key && !isTerminal;
            const isCompleted =
              completedNodes.includes(stg.key) ||
              (isFinalDeliverable && finalStatus === 'succeeded');

            let circleClass = 'pending';
            if (isCompleted) circleClass = 'completed';
            else if (isActive) circleClass = 'active';

            return (
              <div key={stg.key} className={`cv-stage-step-item ${circleClass}`}>
                <div className="cv-stage-step-left">
                  <div className="cv-step-circle">
                    {isCompleted && <IconCheck size={11} color="#22c55e" />}
                    {isActive && <div className="cv-step-pulsing-dot" />}
                  </div>
                  {idx < STAGES.length - 1 && <div className="cv-step-line" />}
                </div>
                <div className="cv-stage-step-label">{stg.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Execution Environment Readiness Card */}
      <div className="cv-card cv-environment-card">
        <h3 className="cv-side-panel-title">Execution environment</h3>
        <div className="cv-env-status-list">
          {/* Local Inference */}
          <div className="cv-env-row">
            <div className="cv-env-label-group">
              <span className="cv-env-icon">🔒</span>
              <span className="cv-env-name">Local Inference</span>
            </div>
            <div className="cv-env-status-val">
              <span className={`cv-status-dot ${sovereignty?.local_inference === 'ok' ? 'green' : 'amber'}`} />
              <span className={sovereignty?.local_inference === 'ok' ? 'cv-text-green' : 'cv-text-amber'}>
                {sovereignty?.local_inference === 'ok' ? 'Ready' : 'Degraded'}
              </span>
            </div>
          </div>

          {/* RAG */}
          <div className="cv-env-row">
            <div className="cv-env-label-group">
              <span className="cv-env-icon">📑</span>
              <span className="cv-env-name">RAG</span>
            </div>
            <div className="cv-env-status-val">
              <span className={`cv-status-dot ${sovereignty?.local_rag === 'ok' ? 'green' : 'amber'}`} />
              <span className={sovereignty?.local_rag === 'ok' ? 'cv-text-green' : 'cv-text-amber'}>
                {sovereignty?.local_rag === 'ok' ? 'Ready' : 'Degraded'}
              </span>
            </div>
          </div>

          {/* OCR */}
          <div className="cv-env-row">
            <div className="cv-env-label-group">
              <span className="cv-env-icon">🖹</span>
              <span className="cv-env-name">OCR</span>
            </div>
            <div className="cv-env-status-val">
              <span className={`cv-status-dot ${sovereignty?.local_ocr === 'ok' ? 'green' : 'amber'}`} />
              <span className={sovereignty?.local_ocr === 'ok' ? 'cv-text-green' : 'cv-text-amber'}>
                {sovereignty?.local_ocr === 'ok' ? 'Ready' : 'Degraded'}
              </span>
            </div>
          </div>

          {/* Docker sandbox */}
          <div className="cv-env-row">
            <div className="cv-env-label-group">
              <span className="cv-env-icon">⚛</span>
              <span className="cv-env-name">Docker sandbox</span>
            </div>
            <div className="cv-env-status-val">
              <span className={`cv-status-dot ${sovereignty?.local_sandbox === 'ok' ? 'green' : 'amber'}`} />
              <span className={sovereignty?.local_sandbox === 'ok' ? 'cv-text-green' : 'cv-text-amber'}>
                {sovereignty?.local_sandbox === 'ok' ? 'Ready' : 'Degraded'}
              </span>
            </div>
          </div>

          {/* Network */}
          <div className="cv-env-row">
            <div className="cv-env-label-group">
              <span className="cv-env-icon">🌐</span>
              <span className="cv-env-name">Network</span>
            </div>
            <div className="cv-env-status-val">
              <span className={`cv-status-dot ${isZeroEgress ? 'muted' : 'amber'}`} />
              <span className="cv-text-muted">
                {isZeroEgress ? 'Isolated' : 'Active'}
              </span>
            </div>
          </div>

          {/* External AI */}
          <div className="cv-env-row">
            <div className="cv-env-label-group">
              <span className="cv-env-icon">⌖</span>
              <span className="cv-env-name">External AI</span>
            </div>
            <div className="cv-env-status-val">
              <span className="cv-status-dot muted" />
              <span className="cv-text-muted">Isolated</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
