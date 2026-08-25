import React from 'react';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { IconAlertTriangle, IconCheck, IconCpu, IconLayers, IconRefresh } from '../common/Icons';
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
    <Card
      title="LangGraph 8-Stage Execution Pipeline"
      icon={<IconLayers size={18} color="#38bdf8" />}
      badge={
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {iteration > 1 && (
            <Badge variant="warning" icon={<IconRefresh size={12} />}>
              Iteration {iteration}/{maxIterations} (Self-Correcting)
            </Badge>
          )}
          {finalStatus === 'succeeded' && (
            <Badge variant="success" icon={<IconCheck size={12} />}>
              Execution Succeeded
            </Badge>
          )}
          {finalStatus === 'failed_bounded' && (
            <Badge variant="warning" icon={<IconAlertTriangle size={12} />}>
              Failed Bounded ({maxIterations} Iterations)
            </Badge>
          )}
          {finalStatus === 'failed' && (
            <Badge variant="error" icon={<IconAlertTriangle size={12} />}>
              Execution Failed
            </Badge>
          )}
          {isStreaming && !finalStatus && (
            <Badge variant="info" icon={<IconCpu size={12} />}>
              Agent Active
            </Badge>
          )}
        </div>
      }
    >
      <div className="graph-container">
        <div className="graph-nodes-grid">
          {STAGES.map((stg) => {
            const isActive = activeNode === stg.key;
            const isCompleted = completedNodes.includes(stg.key);
            const isTerminal = stg.key === 'final_deliverable' && finalStatus !== null;

            let stateClass = 'pending';
            if (isTerminal) {
              stateClass = finalStatus === 'succeeded' ? 'completed' : 'error';
            } else if (isActive) {
              stateClass = 'active';
            } else if (isCompleted) {
              stateClass = 'completed';
            }

            return (
              <div key={stg.key} className={`graph-node ${stateClass}`}>
                <div className="graph-node-header">
                  <span style={{ color: '#64748b' }}>STAGE {stg.stageNum}</span>
                  {isCompleted && !isActive && <IconCheck size={14} color="#10b981" />}
                  {isActive && <span style={{ color: '#38bdf8', fontSize: '0.7rem' }}>RUNNING</span>}
                </div>
                <div className="graph-node-title">{stg.title}</div>
                <div className="graph-node-desc">{stg.description}</div>
              </div>
            );
          })}
        </div>

        {isRetrying && (
          <div style={{
            marginTop: '0.5rem',
            padding: '0.6rem 0.85rem',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: '6px',
            fontSize: '0.775rem',
            color: '#f59e0b',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <IconRefresh size={14} />
            <span>
              <strong>Cyclic Validation Loop:</strong> Validation criteria unmet on step. Re-planning with failure context (Iteration {iteration} of {maxIterations} max allowed).
            </span>
          </div>
        )}
      </div>
    </Card>
  );
};