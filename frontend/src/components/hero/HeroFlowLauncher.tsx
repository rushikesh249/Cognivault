import React, { useEffect, useState } from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  IconAlertTriangle,
  IconCheck,
  IconCode,
  IconCpu,
  IconDownload,
  IconExternalLink,
  IconEye,
  IconFileText,
  IconPlay,
  IconRefresh,
} from '../common/Icons';
import { GraphVisualizer } from '../agent/GraphVisualizer';
import { LiveEventFeed } from '../agent/LiveEventFeed';
import { useTaskStream } from '../../hooks/useTaskStream';
import { api } from '../../services/api';
import type { ArtifactMeta, TaskCreatePayload } from '../../types';

interface HeroFlowLauncherProps {
  onOpenInWorkbench?: (taskId: string) => void;
  onLaunchHeroFlow?: (taskId: string) => void;
}

type HeroType = 'hero1' | 'hero2' | 'hero3';

export const HeroFlowLauncher: React.FC<HeroFlowLauncherProps> = ({
  onOpenInWorkbench,
  onLaunchHeroFlow,
}) => {
  const [activeHeroId, setActiveHeroId] = useState<HeroType | null>(null);
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
    finalStatus,
    taskDetail,
    reconnectCount,
  } = useTaskStream(currentTaskId);

  // Fetch artifacts when task completes
  useEffect(() => {
    if (!currentTaskId) {
      setArtifacts([]);
      return;
    }

    if (finalStatus || !isStreaming) {
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
  }, [currentTaskId, finalStatus, isStreaming]);

  const handleLaunchHero1 = async () => {
    if (isStreaming) {
      setError('An agent task is currently running. Please wait for it to complete or reset.');
      return;
    }

    setLoadingHero('hero1');
    setError(null);
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
      setActiveHeroId('hero1');
      setCurrentTaskId(task.task_id);
      if (onLaunchHeroFlow) {
        onLaunchHeroFlow(task.task_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero Flow 1';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  const handleLaunchHero2 = async () => {
    if (isStreaming) {
      setError('An agent task is currently running. Please wait for it to complete or reset.');
      return;
    }

    setLoadingHero('hero2');
    setError(null);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 2: Coding Agent & Sandbox Self-Correction',
        task_type: 'coding',
        prompt:
          'Implement a recursive factorial function in python with edge case verification. Inject intentional test assertion to trigger cyclic LangGraph self-correction loop in isolated Docker sandbox.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      setActiveHeroId('hero2');
      setCurrentTaskId(task.task_id);
      if (onLaunchHeroFlow) {
        onLaunchHeroFlow(task.task_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero Flow 2';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  const handleLaunchHero3 = async () => {
    if (isStreaming) {
      setError('An agent task is currently running. Please wait for it to complete or reset.');
      return;
    }

    setLoadingHero('hero3');
    setError(null);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 3: Multimodal Vision Inspection Agent',
        task_type: 'vision',
        prompt:
          'Analyze the industrial equipment inspection image. Detail all visible visual observations, surface rust, bolts, flange condition, and pipe connections. Generate the final visual inspection report as a DOCX document.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      setActiveHeroId('hero3');
      setCurrentTaskId(task.task_id);
      if (onLaunchHeroFlow) {
        onLaunchHeroFlow(task.task_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero Flow 3';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  const renderStatusBadge = () => {
    if (isStreaming && !finalStatus) {
      return (
        <Badge variant="info" icon={<IconCpu size={12} />}>
          RUNNING
        </Badge>
      );
    }
    if (finalStatus === 'succeeded') {
      return (
        <Badge variant="success" icon={<IconCheck size={12} />}>
          SUCCEEDED
        </Badge>
      );
    }
    if (finalStatus === 'failed_bounded') {
      return (
        <Badge variant="warning" icon={<IconAlertTriangle size={12} />}>
          BOUNDED
        </Badge>
      );
    }
    if (finalStatus === 'failed') {
      return (
        <Badge variant="error" icon={<IconAlertTriangle size={12} />}>
          FAILED
        </Badge>
      );
    }
    return <Badge variant="neutral">READY</Badge>;
  };

  const getHeroTitle = (id: HeroType | null) => {
    switch (id) {
      case 'hero1':
        return 'Hero Flow 1: Document Intelligence & Artifacts';
      case 'hero2':
        return 'Hero Flow 2: Coding Agent & Sandbox Self-Correction';
      case 'hero3':
        return 'Hero Flow 3: Multimodal Vision Agent';
      default:
        return 'Enterprise Hero Flow';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Section: Overview Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            Enterprise Hero Flows
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Curated end-to-end operational scenarios demonstrating sovereign AI agent capabilities with live in-place execution.
          </p>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: 'var(--status-error-bg)',
            border: '1px solid var(--status-error-border)',
            borderRadius: '8px',
            color: 'var(--status-error)',
            fontSize: '0.85rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Hero Flow Trigger Cards */}
      <div className="grid-3col">
        {/* Hero Flow 1 Card */}
        <Card
          title="Hero Flow 1: Document Intelligence"
          icon={<IconFileText size={18} color="#38bdf8" />}
          badge={activeHeroId === 'hero1' && isStreaming ? <Badge variant="info">ACTIVE</Badge> : undefined}
        >
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '1rem', flex: 1 }}>
            Extracts technical findings via OCR & RAG, cross-references safety standards in knowledge base, and compiles branded DOCX deliverables.
          </p>

          <div
            style={{
              backgroundColor: 'var(--bg-primary)',
              padding: '0.75rem',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.75rem',
              color: '#94a3b8',
              marginBottom: '1rem',
            }}
          >
            <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '0.2rem' }}>
              Deliverable Target:
            </div>
            Structured Technical Analysis Report (DOCX)
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={handleLaunchHero1}
            disabled={isStreaming || loadingHero !== null}
          >
            <IconPlay size={15} />
            {loadingHero === 'hero1' ? 'Launching...' : 'Run Hero 1 (DOCX)'}
          </button>
        </Card>

        {/* Hero Flow 2 Card */}
        <Card
          title="Hero Flow 2: Coding & Self-Correction"
          icon={<IconCode size={18} color="#10b981" />}
          badge={activeHeroId === 'hero2' && isStreaming ? <Badge variant="info">ACTIVE</Badge> : undefined}
        >
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '1rem', flex: 1 }}>
            Executes Python algorithm generation in an air-gapped Docker sandbox with automated pytest execution and cyclic self-correction.
          </p>

          <div
            style={{
              backgroundColor: 'var(--bg-primary)',
              padding: '0.75rem',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.75rem',
              color: '#94a3b8',
              marginBottom: '1rem',
            }}
          >
            <div style={{ color: '#10b981', fontWeight: 600, marginBottom: '0.2rem' }}>
              State Machine Path:
            </div>
            Plan &rarr; Exec &rarr; Fail &rarr; Loop &rarr; Re-plan &rarr; Pass
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={handleLaunchHero2}
            disabled={isStreaming || loadingHero !== null}
          >
            <IconPlay size={15} />
            {loadingHero === 'hero2' ? 'Launching...' : 'Run Hero 2 (Self-Correct)'}
          </button>
        </Card>

        {/* Hero Flow 3 Card */}
        <Card
          title="Hero Flow 3: Multimodal Vision Agent"
          icon={<IconEye size={18} color="#8b5cf6" />}
          badge={activeHeroId === 'hero3' && isStreaming ? <Badge variant="info">ACTIVE</Badge> : undefined}
        >
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '1rem', flex: 1 }}>
            Full LangGraph agent workflow utilizing local Vision-Language Models for industrial inspection with strict non-verdict safety verification.
          </p>

          <div
            style={{
              backgroundColor: 'var(--bg-primary)',
              padding: '0.75rem',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.75rem',
              color: '#94a3b8',
              marginBottom: '1rem',
            }}
          >
            <div style={{ color: '#8b5cf6', fontWeight: 600, marginBottom: '0.2rem' }}>
              Safety Guarantee:
            </div>
            Strict 3-tier findings output (Observations, Hypotheses, Caveats).
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={handleLaunchHero3}
            disabled={isStreaming || loadingHero !== null}
          >
            <IconPlay size={15} />
            {loadingHero === 'hero3' ? 'Launching...' : 'Run Hero 3 (Vision Agent)'}
          </button>
        </Card>
      </div>

      {/* Bottom Section: Live Execution Dashboard */}
      {!currentTaskId ? (
        <Card title="Live Execution & Demo Dashboard" icon={<IconCpu size={18} color="#94a3b8" />}>
          <div
            style={{
              padding: '3rem 1.5rem',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <IconPlay size={24} />
            </div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc' }}>
              Select a Hero Flow above to run a live operational demo
            </h3>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', maxWidth: '600px' }}>
              Watch the sovereign agent execute multi-step planning, tool invocations, Docker sandboxing, or multimodal vision analysis in real-time with full 8-stage state machine tracking.
            </p>
          </div>
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Active Demo Header Bar */}
          <div
            className="wb-card"
            style={{
              padding: '1rem 1.25rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '1rem',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                {getHeroTitle(activeHeroId)}
              </span>
              {renderStatusBadge()}
              {taskDetail?.model_used && (
                <Badge variant="neutral">
                  Model: {taskDetail.model_used}
                </Badge>
              )}
              {iteration > 1 && (
                <Badge variant="warning" icon={<IconRefresh size={12} />}>
                  Iteration {iteration}/{maxIterations} (Self-Correcting)
                </Badge>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {onOpenInWorkbench && currentTaskId && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                  onClick={() => onOpenInWorkbench(currentTaskId)}
                  title="Open this task in the manual Agent Workbench"
                >
                  <IconExternalLink size={14} />
                  Open in Agent Workbench
                </button>
              )}
            </div>
          </div>

          {/* 8-Stage Execution Visualizer */}
          <GraphVisualizer
            activeNode={activeNode}
            completedNodes={completedNodes}
            iteration={iteration}
            maxIterations={maxIterations}
            finalStatus={finalStatus}
            isStreaming={isStreaming}
          />

          {/* Dual Panel: Real-Time Event Feed + Structured Results */}
          <div className="grid-2col">
            {/* Left Column: Live Event Stream */}
            <LiveEventFeed
              events={events}
              isStreaming={isStreaming}
              reconnectCount={reconnectCount}
            />

            {/* Right Column: Hero Demo Results & Deliverables */}
            <Card
              title="Execution Results & Deliverables"
              icon={<IconCheck size={18} color="#10b981" />}
              badge={
                finalStatus === 'succeeded' ? (
                  <Badge variant="success">COMPLETE</Badge>
                ) : isStreaming ? (
                  <Badge variant="info">IN PROGRESS</Badge>
                ) : undefined
              }
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Hero 1 Artifacts */}
                {activeHeroId === 'hero1' && (
                  <div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                      Generated Document Deliverable:
                    </div>
                    {artifacts.length === 0 ? (
                      <div
                        style={{
                          padding: '1.5rem',
                          textAlign: 'center',
                          backgroundColor: 'var(--bg-primary)',
                          borderRadius: '6px',
                          border: '1px dashed var(--border-subtle)',
                          color: '#64748b',
                          fontSize: '0.8rem',
                        }}
                      >
                        {isStreaming
                          ? 'Generating structured analysis report DOCX...'
                          : 'No artifact files registered for this task.'}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {artifacts.map((art) => (
                          <div
                            key={art.artifact_id}
                            style={{
                              padding: '0.75rem 1rem',
                              backgroundColor: 'var(--bg-primary)',
                              borderRadius: '6px',
                              border: '1px solid var(--border-subtle)',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <IconFileText size={18} color="#38bdf8" />
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>
                                  {art.title}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                                  {art.kind.toUpperCase()} &bull; ID: {art.artifact_id.substring(0, 12)}...
                                </div>
                              </div>
                            </div>
                            <a
                              href={api.getArtifactDownloadUrl(art.artifact_id)}
                              className="btn btn-primary"
                              style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                              download
                            >
                              <IconDownload size={13} />
                              Download File
                            </a>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Hero 2 Self-Correction Journey */}
                {activeHeroId === 'hero2' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      Cyclic Self-Correction Lifecycle:
                    </div>

                    <div
                      style={{
                        padding: '0.75rem',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: '6px',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <Badge variant="warning">Iteration 1</Badge>
                        <span style={{ fontWeight: 600, color: '#f8fafc' }}>Docker Sandbox Pytest Execution</span>
                      </div>
                      <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: 0 }}>
                        Intentional defect injected: <code>factorial(0) == 0</code>. Pytest detected assertion error in container sandbox.
                      </p>
                    </div>

                    <div
                      style={{
                        padding: '0.75rem',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: '6px',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <Badge variant="info">Observation</Badge>
                        <span style={{ fontWeight: 600, color: '#f8fafc' }}>LangGraph Replanning & Code Repair</span>
                      </div>
                      <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: 0 }}>
                        Agent parsed test failure stderr, scheduled code repair, and patched recursive base case in sandbox.
                      </p>
                    </div>

                    <div
                      style={{
                        padding: '0.75rem',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: '6px',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <Badge variant="success">Iteration 2</Badge>
                        <span style={{ fontWeight: 600, color: '#f8fafc' }}>Re-Verification in Isolated Container</span>
                      </div>
                      <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: 0 }}>
                        Re-executed test suite with <code>--network none</code>. All assertions passed with exit code 0.
                      </p>
                    </div>
                  </div>
                )}

                {/* Hero 3 Vision Findings & Deliverables */}
                {activeHeroId === 'hero3' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      Multimodal Vision Analysis Details:
                    </div>

                    <div
                      style={{
                        padding: '0.75rem',
                        backgroundColor: 'var(--bg-primary)',
                        borderRadius: '6px',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ color: '#8b5cf6', fontWeight: 600, marginBottom: '0.25rem' }}>
                        Local Vision-Language Model:
                      </div>
                      <span style={{ color: '#f8fafc', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                        {taskDetail?.model_used || 'Resolving model...'}
                      </span>
                    </div>

                    {artifacts.length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                          Visual Inspection Report Deliverable:
                        </div>
                        {artifacts.map((art) => (
                          <div
                            key={art.artifact_id}
                            style={{
                              padding: '0.75rem 1rem',
                              backgroundColor: 'var(--bg-primary)',
                              borderRadius: '6px',
                              border: '1px solid var(--border-subtle)',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <IconFileText size={18} color="#8b5cf6" />
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>
                                  {art.title}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                                  {art.kind.toUpperCase()} &bull; ID: {art.artifact_id.substring(0, 12)}...
                                </div>
                              </div>
                            </div>
                            <a
                              href={api.getArtifactDownloadUrl(art.artifact_id)}
                              className="btn btn-primary"
                              style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                              download
                            >
                              <IconDownload size={13} />
                              Download File
                            </a>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Task Metadata Footer */}
                {taskDetail && (
                  <div
                    style={{
                      paddingTop: '0.5rem',
                      borderTop: '1px solid var(--border-subtle)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.75rem',
                      color: '#64748b',
                    }}
                  >
                    <span>Task ID: <code style={{ color: '#38bdf8' }}>{taskDetail.task_id.substring(0, 12)}...</code></span>
                    <span>Created: {new Date(taskDetail.created_at).toLocaleTimeString()}</span>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};