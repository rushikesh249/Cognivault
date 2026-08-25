import React, { useState } from 'react';
import { Card } from '../common/Card';
import { IconCode, IconEye, IconFileText, IconPlay } from '../common/Icons';
import { api } from '../../services/api';
import type { TaskCreatePayload } from '../../types';

interface HeroFlowLauncherProps {
  onLaunchHeroFlow: (taskId: string) => void;
}

export const HeroFlowLauncher: React.FC<HeroFlowLauncherProps> = ({ onLaunchHeroFlow }) => {
  const [docFormat, setDocFormat] = useState<'docx' | 'xlsx' | 'pptx' | 'pdf'>('docx');
  const [loadingHero, setLoadingHero] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLaunchHero1 = async () => {
    setLoadingHero('hero1');
    setError(null);
    try {
      const formatPrompts = {
        docx: 'Extract findings and anomalies from inspection report, search safety standards in knowledge base, evaluate compliance gaps, and generate technical Approval Note DOCX artifact.',
        xlsx: 'Extract equipment test records and metrics from inspection report, evaluate safety limits in knowledge base, and generate technical inspection summary XLSX artifact.',
        pptx: 'Extract findings from inspection report, summarize safety compliance gaps against standard clauses, and generate management summary deck PPTX artifact.',
        pdf: 'Extract findings and anomalies from inspection report, evaluate safety standards, and generate technical inspection report PDF artifact.',
      };

      const payload: TaskCreatePayload = {
        title: `Hero 1: Document Intelligence (${docFormat.toUpperCase()})`,
        task_type: 'document',
        prompt: formatPrompts[docFormat],
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      onLaunchHeroFlow(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero Flow 1';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  const handleLaunchHero2 = async () => {
    setLoadingHero('hero2');
    setError(null);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 2: Coding Agent & Sandbox Self-Correction',
        task_type: 'coding',
        prompt: 'Implement a recursive factorial function in python with edge case verification. Inject intentional test assertion to trigger cyclic LangGraph self-correction loop in isolated Docker sandbox.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      onLaunchHeroFlow(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero Flow 2';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  const handleLaunchHero3 = async () => {
    setLoadingHero('hero3');
    setError(null);
    try {
      const payload: TaskCreatePayload = {
        title: 'Hero 3: Multimodal Vision Inspection Agent',
        task_type: 'vision',
        prompt: 'Analyze industrial turbine blade photograph. Segregate factual visual observations, plausible AI engineering hypotheses, and explicit uncertainty hedges without issuing certified statutory verdicts.',
        file_ids: [],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      onLaunchHeroFlow(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch Hero Flow 3';
      setError(msg);
    } finally {
      setLoadingHero(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            Enterprise Hero Flows
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Curated end-to-end operational scenarios demonstrating sovereign AI agent capabilities.
          </p>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: 'var(--status-error-bg)',
          border: '1px solid var(--status-error-border)',
          borderRadius: '8px',
          color: 'var(--status-error)',
          fontSize: '0.85rem'
        }}>
          {error}
        </div>
      )}

      <div className="grid-3col">
        {/* Hero Flow 1 */}
        <Card
          title="Hero Flow 1: Document Intelligence & Artifacts"
          icon={<IconFileText size={18} color="#38bdf8" />}
        >
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '1rem', flex: 1 }}>
            Extracts technical findings via OCR & RAG, checks ISO compliance gaps, and compiles branded deliverables.
          </p>

          <div className="form-group">
            <label className="form-label">Deliverable Format</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.35rem' }}>
              {(['docx', 'xlsx', 'pptx', 'pdf'] as const).map((fmt) => (
                <button
                  key={fmt}
                  type="button"
                  className={`btn ${docFormat === fmt ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '0.35rem 0.2rem', fontSize: '0.75rem', textTransform: 'uppercase' }}
                  onClick={() => setDocFormat(fmt)}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '0.5rem' }}
            onClick={handleLaunchHero1}
            disabled={loadingHero !== null}
          >
            <IconPlay size={15} />
            {loadingHero === 'hero1' ? 'Launching...' : `Run Hero 1 (${docFormat.toUpperCase()})`}
          </button>
        </Card>

        {/* Hero Flow 2 */}
        <Card
          title="Hero Flow 2: Coding Agent & Self-Correction"
          icon={<IconCode size={18} color="#10b981" />}
        >
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '1rem', flex: 1 }}>
            Executes Python algorithm generation inside an isolated Docker sandbox with automated test parsing and cyclic self-correction.
          </p>

          <div style={{
            backgroundColor: 'var(--bg-primary)',
            padding: '0.75rem',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.75rem',
            color: '#94a3b8',
            marginBottom: '1rem'
          }}>
            <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '0.2rem' }}>State Machine Path:</div>
            Plan &rarr; Exec &rarr; Fail &rarr; Loop &rarr; Re-plan &rarr; Pass
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%' }}
            onClick={handleLaunchHero2}
            disabled={loadingHero !== null}
          >
            <IconPlay size={15} />
            {loadingHero === 'hero2' ? 'Launching...' : 'Run Hero 2 (Self-Correct)'}
          </button>
        </Card>

        {/* Hero Flow 3 */}
        <Card
          title="Hero Flow 3: Multimodal Vision Agent"
          icon={<IconEye size={18} color="#8b5cf6" />}
        >
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '1rem', flex: 1 }}>
            Full LangGraph agent workflow utilizing local Vision-Language Models for industrial inspection with strict non-verdict safety verification.
          </p>

          <div style={{
            backgroundColor: 'var(--bg-primary)',
            padding: '0.75rem',
            borderRadius: '6px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.75rem',
            color: '#94a3b8',
            marginBottom: '1rem'
          }}>
            <div style={{ color: '#8b5cf6', fontWeight: 600, marginBottom: '0.2rem' }}>Safety Guarantee:</div>
            Strict 3-tier findings output (Observations, Hypotheses, Caveats).
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%' }}
            onClick={handleLaunchHero3}
            disabled={loadingHero !== null}
          >
            <IconPlay size={15} />
            {loadingHero === 'hero3' ? 'Launching...' : 'Run Hero 3 (Vision Agent)'}
          </button>
        </Card>
      </div>
    </div>
  );
};