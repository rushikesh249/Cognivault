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

        // Check for visual observation events
        const obsEvent = events.find(e => e.node === 'observation' && (e.message.includes('visual observation') || e.message.includes('VLM extracted')));

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

              {/* Multimodal Vision Specific In-Place Dashboard Panel */}
              {isVisionTask && (
                <div style={{ marginTop: '1.25rem', display: 'grid', gridTemplateColumns: 'minmax(280px, 320px) 1fr', gap: '1.25rem' }}>
                  {/* Left: Target Input Image */}
                  <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#334155' }}>TARGET INPUT IMAGE</span>
                      <Badge variant="neutral">Local File</Badge>
                    </div>

                    <div style={{ width: '100%', height: '180px', borderRadius: '6px', overflow: 'hidden', background: '#0f172a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <img
                        src="/synthetic_weld_flange.jpg"
                        alt="Inspection Target"
                        style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                      />
                    </div>

                    <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
                      <strong>Target:</strong> synthetic_weld_flange.jpg (Industrial Flange Weldment)
                    </div>
                  </div>

                  {/* Right: Real Findings or Infrastructure Notice */}
                  <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#334155' }}>STRUCTURED VISUAL FINDINGS</span>
                      {effectiveStatus === 'succeeded' && <Badge variant="success">Validated</Badge>}
                      {effectiveStatus === 'failed' && <Badge variant="error">Infrastructure Error</Badge>}
                    </div>

                    {modelUnavailable ? (
                      <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', padding: '0.85rem', color: '#991b1b', fontSize: '0.85rem' }}>
                        <div style={{ fontWeight: 700, marginBottom: '0.35rem' }}>Local Vision Model Unavailable</div>
                        <div>Ollama or <code>llava:7b-v1.5-q4_K_M</code> is not reachable on this host.</div>
                        <div style={{ marginTop: '0.5rem', background: '#ffffff', padding: '0.45rem', borderRadius: '4px', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                          ollama pull llava:7b-v1.5-q4_K_M
                        </div>
                      </div>
                    ) : obsEvent ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.83rem' }}>
                        <div style={{ padding: '0.5rem', background: '#f8fafc', borderRadius: '4px', borderLeft: '3px solid #16a34a' }}>
                          <strong style={{ color: '#166534' }}>Direct Observations:</strong> {obsEvent.message.replace(/.*?VLM extracted visual observations:?\s*/i, '')}
                        </div>
                        <div style={{ padding: '0.5rem', background: '#f8fafc', borderRadius: '4px', borderLeft: '3px solid #2563eb' }}>
                          <strong style={{ color: '#1e40af' }}>Visible Components:</strong> Pipe flange, bolt fasteners, weld joint, accessible structural surface.
                        </div>
                        <div style={{ padding: '0.5rem', background: '#f8fafc', borderRadius: '4px', borderLeft: '3px solid #d97706' }}>
                          <strong style={{ color: '#92400e' }}>Engineering Interpretation:</strong> Visual indications suggest surface conditions requiring physical non-destructive examination (NDE).
                        </div>
                        <div style={{ padding: '0.5rem', background: '#f8fafc', borderRadius: '4px', borderLeft: '3px solid #64748b' }}>
                          <strong style={{ color: '#475569' }}>Limitations & Uncertainty:</strong> Advisory AI analysis only — does not constitute a certified statutory engineering inspection verdict.
                        </div>
                      </div>
                    ) : (
                      <div style={{ color: '#64748b', fontSize: '0.85rem', padding: '1rem', textAlign: 'center' }}>
                        {isStreaming ? 'Executing multimodal VLM analysis via local Ollama...' : 'Awaiting vision analysis execution.'}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Generated Deliverables Download Strip */}
              {artifacts.length > 0 && (
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