import React, { useEffect, useState } from 'react';
import { Badge } from '../common/Badge';
import {
  IconCheck,
  IconCode,
  IconCpu,
  IconDownload,
  IconEye,
  IconFileText,
  IconPlay,
} from '../common/Icons';
import { GraphVisualizer } from '../agent/GraphVisualizer';
import { LiveEventFeed } from '../agent/LiveEventFeed';
import { HeroVisionInspector } from './HeroVisionInspector';
import { useTaskStream } from '../../hooks/useTaskStream';
import { api } from '../../services/api';
import type { ArtifactMeta, TaskCreatePayload } from '../../types';

interface HeroFlowLauncherProps {
  onOpenInWorkbench?: (taskId: string) => void;
}

type HeroType = 'hero1' | 'hero2' | 'hero3';

export const HeroFlowLauncher: React.FC<HeroFlowLauncherProps> = ({ onOpenInWorkbench }) => {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [loadingHero, setLoadingHero] = useState<HeroType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactMeta[]>([]);

  // Live SSE stream and state machine tracking for active hero task
  const {
    events,
    activeNode,
    completedNodes,
    iteration,
    maxIterations,
    isStreaming,
    isComplete,
    finalStatus,
    taskDetail,
    reconnectCount,
    reset,
  } = useTaskStream(currentTaskId);

  const isTerminal = Boolean(finalStatus) || isComplete || (taskDetail && ['succeeded', 'failed', 'failed_bounded'].includes(taskDetail.status));
  const effectiveStatus = finalStatus || taskDetail?.status || null;

  // Fetch artifacts when task completes
  useEffect(() => {
    if (!currentTaskId) return;

    if (isTerminal || !isStreaming) {
      let isMounted = true;
      api
        .listArtifacts(50, 0)
        .then((allArtifacts) => {
          if (isMounted) {
            const taskArts = allArtifacts.filter((a) => a.task_id === currentTaskId);
            setArtifacts(taskArts);
          }
        })
        .catch((err) => {
          console.warn('Failed to load artifacts for hero task:', err);
        });

      return () => {
        isMounted = false;
      };
    }
  }, [currentTaskId, isTerminal, isStreaming]);

  // Launch Hero 1: Document Intelligence
  const handleLaunchHero1 = async () => {
    if (isStreaming && !isTerminal) {
      setError('An agent task is currently running. Please wait for it to complete.');
      return;
    }

    reset();
    setLoadingHero('hero1');
    setError(null);
    setArtifacts([]);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 1: Document Intelligence (DOCX)',
        task_type: 'document',
        prompt:
          'Extract findings and anomalies from inspection report, search safety standards in knowledge base, evaluate compliance gaps, and generate technical structured analysis report DOCX artifact.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      setCurrentTaskId(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero 1';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  // Launch Hero 2: Coding & Self-Correction
  const handleLaunchHero2 = async () => {
    if (isStreaming && !isTerminal) {
      setError('An agent task is currently running. Please wait for it to complete.');
      return;
    }

    reset();
    setLoadingHero('hero2');
    setError(null);
    setArtifacts([]);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 2: Coding Self-Correction (Python/Docker)',
        task_type: 'coding',
        prompt:
          'Write a python recursive factorial algorithm with unit tests. Execute tests inside Docker sandbox, verify exit codes, and self-correct logic until 100% assertions pass.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      setCurrentTaskId(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero 2';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  // Launch Hero 3: Multimodal Vision
  const handleLaunchHero3 = async () => {
    if (isStreaming && !isTerminal) {
      setError('An agent task is currently running. Please wait for it to complete.');
      return;
    }

    reset();
    setLoadingHero('hero3');
    setError(null);
    setArtifacts([]);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 3: Multimodal Inspection Analysis (Image)',
        task_type: 'vision',
        prompt:
          'Perform multimodal defect classification and measurement on inspection target. Identify anomaly locations, structural risk severity, and produce technical findings.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      setCurrentTaskId(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero 3';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  return (
    <div className="cv-view-layout">
      <div className="cv-section-header-row">
        <div>
          <h2 className="cv-section-title">Workflow Library & Preconfigured Agents</h2>
          <p className="cv-section-subtitle">
            Autonomous sovereign agent workflows designed for document extraction, sandboxed code correction, and multimodal inspection.
          </p>
        </div>
      </div>

      {error && <div className="cv-form-error-banner">{error}</div>}

      {/* Enterprise Cards Grid */}
      <div className="cv-workflow-grid">
        {/* Card 1: Document Intelligence */}
        <div className="cv-card cv-workflow-card">
          <div className="cv-workflow-top-row">
            <span className="cv-workflow-badge-tag">DOCX ARTIFACT</span>
            <IconFileText size={18} color="#4338ca" />
          </div>

          <div className="cv-workflow-title">Document Intelligence</div>
          <p className="cv-workflow-desc">
            Autonomous RAG pipeline for extracting unstructured findings, cross-referencing safety standards, and synthesizing branded compliance DOCX reports.
          </p>

          <div className="cv-workflow-specs">
            <div className="cv-spec-row">
              <span className="cv-spec-key">Model Pipeline</span>
              <span className="cv-spec-val">qwen2.5:7b-instruct-q4_K_M</span>
            </div>
            <div className="cv-spec-row">
              <span className="cv-spec-key">Vector Engine</span>
              <span className="cv-spec-val">ChromaDB On-Premise</span>
            </div>
            <div className="cv-spec-row">
              <span className="cv-spec-key">Air-Gap Egress</span>
              <span className="cv-spec-val cv-text-green">0.00 MB (Isolated)</span>
            </div>
          </div>

          <button
            type="button"
            className="cv-btn-purple-action"
            onClick={handleLaunchHero1}
            disabled={loadingHero !== null || (isStreaming && !isTerminal)}
          >
            <IconPlay size={14} />
            <span>{loadingHero === 'hero1' ? 'Initializing...' : 'Run Document Intelligence'}</span>
          </button>
        </div>

        {/* Card 2: Coding Self-Correction */}
        <div className="cv-card cv-workflow-card">
          <div className="cv-workflow-top-row">
            <span className="cv-workflow-badge-tag">DOCKER SANDBOX</span>
            <IconCode size={18} color="#4338ca" />
          </div>

          <div className="cv-workflow-title">Coding Self-Correction</div>
          <p className="cv-workflow-desc">
            Cyclic LangGraph code generator with isolated container sandbox execution, automated test execution, stderr inspection, and iterative repair.
          </p>

          <div className="cv-workflow-specs">
            <div className="cv-spec-row">
              <span className="cv-spec-key">Model Pipeline</span>
              <span className="cv-spec-val">qwen2.5-coder:7b-instruct-q4_K_M</span>
            </div>
            <div className="cv-spec-row">
              <span className="cv-spec-key">Sandbox Mode</span>
              <span className="cv-spec-val">Isolated Docker (cgroups)</span>
            </div>
            <div className="cv-spec-row">
              <span className="cv-spec-key">Max Iterations</span>
              <span className="cv-spec-val">6 Bounded Cycles</span>
            </div>
          </div>

          <button
            type="button"
            className="cv-btn-purple-action"
            onClick={handleLaunchHero2}
            disabled={loadingHero !== null || (isStreaming && !isTerminal)}
          >
            <IconPlay size={14} />
            <span>{loadingHero === 'hero2' ? 'Initializing...' : 'Run Code Self-Correction'}</span>
          </button>
        </div>

        {/* Card 3: Multimodal Vision */}
        <div className="cv-card cv-workflow-card">
          <div className="cv-workflow-top-row">
            <span className="cv-workflow-badge-tag">LOCAL VLM</span>
            <IconEye size={18} color="#4338ca" />
          </div>

          <div className="cv-workflow-title">Multimodal Vision</div>
          <p className="cv-workflow-desc">
            Local vision-language model diagnostic flow detecting physical defects, evaluating confidence bounds, and producing structured observations.
          </p>

          <div className="cv-workflow-specs">
            <div className="cv-spec-row">
              <span className="cv-spec-key">Model Pipeline</span>
              <span className="cv-spec-val">llava:7b-v1.5-q4_K_M</span>
            </div>
            <div className="cv-spec-row">
              <span className="cv-spec-key">Inference Host</span>
              <span className="cv-spec-val">Ollama Local (On-Premise)</span>
            </div>
            <div className="cv-spec-row">
              <span className="cv-spec-key">External AI Calls</span>
              <span className="cv-spec-val cv-text-green">0 (Strictly On-Premise)</span>
            </div>
          </div>

          <button
            type="button"
            className="cv-btn-purple-action"
            onClick={handleLaunchHero3}
            disabled={loadingHero !== null || (isStreaming && !isTerminal)}
          >
            <IconPlay size={14} />
            <span>{loadingHero === 'hero3' ? 'Initializing...' : 'Run Vision Diagnostics'}</span>
          </button>
        </div>
      </div>

      {/* Active Hero Execution Progress & Details */}
      {currentTaskId && (() => {
        const isVisionTask =
          taskDetail?.task_type === 'vision' ||
          (taskDetail?.title || '').toLowerCase().includes('vision') ||
          (taskDetail?.title || '').toLowerCase().includes('hero 3');

        const activeModelName =
          taskDetail?.model_used ||
          (isVisionTask ? 'llava:7b-v1.5-q4_K_M' : taskDetail?.task_type === 'coding' ? 'qwen2.5-coder:7b' : 'qwen2.5:7b-instruct');

        // Check for model health / infrastructure warnings in stream
        const healthEvent = events.find((e) => e.message.includes('[model_health]') || e.message.includes('Infrastructure failure'));
        const modelUnavailable = Boolean(healthEvent) || (effectiveStatus === 'failed' && events.some(e => e.message.toLowerCase().includes('unavailable') || e.message.toLowerCase().includes('timeout')));

        return (
          <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="cv-card">
              <div className="cv-card-header-row">
                <div className="cv-card-title-group">
                  <IconCpu size={16} color="#4338ca" />
                  <h3 className="cv-card-heading">
                    Active Workflow Execution ({taskDetail?.title || currentTaskId})
                  </h3>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <Badge variant="neutral">Model: {activeModelName}</Badge>
                  <Badge variant="info">Cycle: {iteration} / {maxIterations}</Badge>

                  {effectiveStatus && (
                    <Badge
                      variant={
                        effectiveStatus === 'succeeded'
                          ? 'success'
                          : effectiveStatus === 'failed_bounded'
                          ? 'warning'
                          : effectiveStatus === 'failed'
                          ? 'error'
                          : 'info'
                      }
                    >
                      {effectiveStatus.toUpperCase()}
                    </Badge>
                  )}

                  {onOpenInWorkbench && (
                    <button
                      type="button"
                      className="cv-btn-compact-secondary"
                      onClick={() => onOpenInWorkbench(currentTaskId)}
                    >
                      Open in Workbench &rarr;
                    </button>
                  )}
                </div>
              </div>

              {/* 8-Stage Execution Graph */}
              <GraphVisualizer
                activeNode={activeNode}
                completedNodes={completedNodes}
                iteration={iteration}
                maxIterations={maxIterations}
                finalStatus={effectiveStatus}
                isStreaming={isStreaming}
              />

              {/* Multimodal Vision Specific Professional Inspection Inspector */}
              {isVisionTask && (
                <HeroVisionInspector
                  taskDetail={taskDetail}
                  events={events}
                  isStreaming={isStreaming}
                  isTerminal={Boolean(isTerminal)}
                  effectiveStatus={effectiveStatus}
                  modelUnavailable={modelUnavailable}
                  artifacts={artifacts}
                  activeNode={activeNode}
                  iteration={iteration}
                  maxIterations={maxIterations}
                />
              )}

              {/* Generated Deliverables Download Strip (For Document and Coding tasks) */}
              {!isVisionTask && artifacts.length > 0 && (
                <div className="cv-task-deliverables-section" style={{ marginTop: '1rem' }}>
                  <div className="cv-deliverables-header">
                    <span className="cv-deliverables-title">
                      <IconCheck size={14} color="#16a34a" />
                      Generated Deliverables ({artifacts.length}):
                    </span>
                  </div>
                  <div className="cv-deliverables-buttons">
                    {artifacts.map((art) => (
                      <a
                        key={art.artifact_id}
                        href={api.getArtifactDownloadUrl(art.artifact_id)}
                        className="cv-btn-deliverable-download"
                        download
                      >
                        <IconDownload size={13} />
                        <span>Download {art.title} ({art.kind.toUpperCase()})</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Real-time SSE Stream Logs */}
            <LiveEventFeed
              events={events}
              isStreaming={isStreaming}
              reconnectCount={reconnectCount}
            />
          </div>
        );
      })()}
    </div>
  );
};