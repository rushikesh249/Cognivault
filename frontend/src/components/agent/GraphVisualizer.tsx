import React from 'react';
import { Badge } from '../common/Badge';
import {
  IconAlertTriangle,
  IconCheck,
  IconCpu,
  IconLayers,
  IconRefresh,
} from '../common/Icons';
import type { LangGraphNode, TaskStatus } from '../../types';

interface GraphVisualizerProps {
  activeNode: LangGraphNode | null;
  completedNodes: LangGraphNode[];
  iteration: number;
  maxIterations: number;
  finalStatus: TaskStatus | null;
  isStreaming: boolean;
}

interface NodeDefinition {
  key: LangGraphNode;
  title: string;
  stageNum: number;
  description: string;
}

const STAGES: NodeDefinition[] = [
  { key: 'task_understanding', stageNum: 1, title: 'Task Understanding', description: 'Parse intent & input requirements' },
  { key: 'planning', stageNum: 2, title: 'Planning & Strategy', description: 'Deconstruct goal into executable steps' },
  { key: 'model_selection', stageNum: 3, title: 'Model Selection', description: 'Select optimal sovereign local model' },
  { key: 'tool_selection', stageNum: 4, title: 'Tool Selection', description: 'Authorize sandboxed tool permissions' },
  { key: 'execution', stageNum: 5, title: 'Tool Execution', description: 'Run code/RAG/OCR in isolated sandbox' },
  { key: 'observation', stageNum: 6, title: 'Observation', description: 'Normalize and validate raw outputs' },
  { key: 'validation', stageNum: 7, title: 'Validation & Quality', description: 'Verification check with loop-back' },
  { key: 'final_deliverable', stageNum: 8, title: 'Final Deliverable', description: 'Persist artifacts & deliver results' },
];

export const GraphVisualizer: React.FC<GraphVisualizerProps> = ({
  activeNode,
  completedNodes,
  iteration,
  maxIterations,
  finalStatus,
  isStreaming,
}) => {
  const isRetrying = iteration > 1 && (activeNode === 'planning' || activeNode === 'validation');

  return (
    <div className="cv-card cv-graph-card">
      <div className="cv-card-header-row">
        <div className="cv-card-title-group">
          <IconLayers size={18} color="#4338ca" />
          <h3 className="cv-card-heading">LangGraph 8-Stage Execution Pipeline</h3>
        </div>

        <div className="cv-header-badges-row" style={{ display: 'flex', gap: '0.5rem' }}>
          {iteration > 1 && (
            <Badge variant="warning" icon={<IconRefresh size={13} />}>
              Iteration {iteration}/{maxIterations} (Self-Correcting)
            </Badge>
          )}
          {finalStatus === 'succeeded' && (
            <Badge variant="success" icon={<IconCheck size={13} />}>
              Execution Succeeded
            </Badge>
          )}
          {finalStatus === 'failed_bounded' && (
            <Badge variant="warning" icon={<IconAlertTriangle size={13} />}>
              Failed Bounded ({maxIterations} Iterations)
            </Badge>
          )}
          {finalStatus === 'failed' && (
            <Badge variant="error" icon={<IconAlertTriangle size={13} />}>
              Execution Failed
            </Badge>
          )}
          {isStreaming && !finalStatus && (
            <Badge variant="info" icon={<IconCpu size={13} />}>
              Agent Active
            </Badge>
          )}
        </div>
      </div>

      <div className="cv-graph-grid">
        {STAGES.map((stg) => {
          const isFinalDeliverable = stg.key === 'final_deliverable';
          const isTerminal = isFinalDeliverable && finalStatus !== null;
          const isActive = activeNode === stg.key && !isTerminal;
          const isCompleted =
            completedNodes.includes(stg.key) ||
            (isFinalDeliverable && finalStatus === 'succeeded');

          let stateClass = 'pending';
          if (isTerminal) {
            if (finalStatus === 'succeeded') stateClass = 'completed';
            else if (finalStatus === 'failed_bounded') stateClass = 'warning';
            else stateClass = 'error';
          } else if (isActive) {
            stateClass = 'active';
          } else if (isCompleted) {
            stateClass = 'completed';
          }

          return (
            <div key={stg.key} className={`cv-graph-node-box ${stateClass}`}>
              <div className="cv-graph-node-top">
                <span className="cv-stage-num-tag">STAGE {stg.stageNum}</span>
                {isTerminal ? (
                  finalStatus === 'succeeded' ? (
                    <span className="cv-node-status-badge cv-text-green">
                      <IconCheck size={14} color="#15803d" /> SUCCEEDED
                    </span>
                  ) : finalStatus === 'failed_bounded' ? (
                    <span className="cv-node-status-badge cv-text-amber">
                      <IconAlertTriangle size={14} color="#b45309" /> BOUNDED
                    </span>
                  ) : (
                    <span className="cv-node-status-badge cv-text-red">
                      <IconAlertTriangle size={14} color="#b91c1c" /> FAILED
                    </span>
                  )
                ) : isActive ? (
                  <span className="cv-node-status-badge cv-text-purple">RUNNING</span>
                ) : isCompleted ? (
                  <IconCheck size={15} color="#15803d" />
                ) : null}
              </div>
              <div className="cv-graph-node-title">{stg.title}</div>
              <div className="cv-graph-node-desc">{stg.description}</div>
            </div>
          );
        })}
      </div>

      {isRetrying && (
        <div className="cv-graph-retry-banner">
          <IconRefresh size={15} />
          <span>
            <strong>Cyclic Validation Loop:</strong> Validation criteria unmet on step. Re-planning with failure context (Iteration {iteration} of {maxIterations} max allowed).
          </span>
        </div>
      )}
    </div>
  );
};