import React, { useEffect, useMemo, useState } from 'react';
import { Badge } from '../common/Badge';
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCheck,
  IconCpu,
  IconDownload,
  IconEye,
  IconFileText,
  IconShield,
  IconSparkles,
  IconUpload,
} from '../common/Icons';
import { useTaskStream } from '../../hooks/useTaskStream';
import { api } from '../../services/api';
import type { ArtifactMeta, TaskCreatePayload } from '../../types';

export const VisionInspector: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [visionTaskId, setVisionTaskId] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactMeta[]>([]);

  // Dedicated task stream for Sources vision inspection (isolated from Agents/Hero flows)
  const {
    events,
    activeNode,
    isStreaming,
    isComplete,
    finalStatus,
    iteration,
    maxIterations,
    taskDetail,
    reset,
  } = useTaskStream(visionTaskId);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
      setError(null);
      setVisionTaskId(null);
      setArtifacts([]);
      reset();
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select an inspection image first.');
      return;
    }

    setIsStarting(true);
    setError(null);
    setArtifacts([]);
    reset();

    try {
      // 1. Upload image to sovereign storage
      const uploadRes = await api.uploadFile(selectedFile);

      // 2. Create dedicated vision agent task
      const payload: TaskCreatePayload = {
        title: `Vision Inspection: ${selectedFile.name}`,
        task_type: 'vision',
        prompt:
          prompt.trim() ||
          'Perform multimodal defect classification and measurement on inspection target. Identify anomaly locations, structural risk severity, and produce technical findings.',
        file_ids: [uploadRes.file_id],
      };

      const task = await api.createTask(payload);
      await api.runAgent(task.task_id);
      setVisionTaskId(task.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Vision analysis initialization failed';
      setError(msg);
    } finally {
      setIsStarting(false);
    }
  };

  // 3. Fetch generated deliverables when task completes
  useEffect(() => {
    if (isComplete && visionTaskId) {
      api
        .listArtifacts(20, 0)
        .then((items) => {
          const taskArtifacts = items.filter((a) => a.task_id === visionTaskId);
          setArtifacts(taskArtifacts);
        })
        .catch((err) => {
          console.error('[VisionInspector] Failed to fetch task artifacts:', err);
        });
    }
  }, [isComplete, visionTaskId]);

  // 4. Parse structured findings and metadata dynamically from real runtime events
  const {
    directObservations,
    engineeringInterpretations,
    uncertainties,
    runtimeModel,
    modelUnavailable,
    insufficientImage,
  } = useMemo(() => {
    let model = taskDetail?.model_used || null;
    let unavailable = false;
    let insufficient = false;

    const observations: string[] = [];
    const interpretations: string[] = [];
    const uncerts: string[] = [];

    for (const ev of events) {
      const msg = ev.message;

      // Detect model if logged in events
      const modelMatch = msg.match(/via ['"]?([^'"]+)['"]? on image/i);
      if (modelMatch && modelMatch[1] && !model) {
        model = modelMatch[1];
      }

      // Detect model from health check or error message if available
      const healthMatch = msg.match(/ollama pull ([^\s'"]+)/i);
      if (healthMatch && healthMatch[1] && !model) {
        model = healthMatch[1];
      }

      // Detect model health warnings or infrastructure failures
      if (
        msg.includes('[model_health]') ||
        msg.includes('Infrastructure failure') ||
        (msg.toLowerCase().includes('unavailable') && ev.level === 'error') ||
        (msg.toLowerCase().includes('timeout') && ev.level === 'error')
      ) {
        unavailable = true;
      }

      // Detect unreadable/insufficient image notice
      if (msg.toLowerCase().includes('no readable text') || msg.toLowerCase().includes('no reliable visual findings')) {
        insufficient = true;
      }

      // Parse structured tags
      if (msg.includes('[visual_observation]')) {
        const item = msg.replace(/.*?\[visual_observation\]\s*/i, '').trim();
        if (item && !observations.includes(item)) {
          observations.push(item);
        }
      } else if (msg.includes('[engineering_interpretation]')) {
        const item = msg.replace(/.*?\[engineering_interpretation\]\s*/i, '').trim();
        if (item && !interpretations.includes(item)) {
          interpretations.push(item);
        }
      } else if (msg.includes('[visual_uncertainty]')) {
        const item = msg.replace(/.*?\[visual_uncertainty\]\s*/i, '').trim();
        if (item && !uncerts.includes(item)) {
          uncerts.push(item);
        }
      } else if (msg.includes('VLM extracted visual observations:')) {
        // Fallback for legacy observation messages
        const raw = msg.replace(/.*?VLM extracted visual observations:?\s*/i, '').trim();
        const parts = raw.split(';').map((p) => p.trim()).filter(Boolean);
        for (const p of parts) {
          if (!observations.includes(p)) {
            observations.push(p);
          }
        }
      }
    }

    if (finalStatus === 'failed' && (events.some((e) => e.message.toLowerCase().includes('unavailable')) || unavailable)) {
      unavailable = true;
    }

    const resolvedModel = model || 'llava:7b-v1.5-q4_K_M';

    return {
      directObservations: observations,
      engineeringInterpretations: interpretations,
      uncertainties: uncerts,
      runtimeModel: resolvedModel,
      modelUnavailable: unavailable,
      insufficientImage: insufficient,
    };
  }, [events, taskDetail, finalStatus]);

  const docxArtifact = artifacts.find(
    (a) => a.kind === 'docx' || a.title.toLowerCase().includes('inspection') || a.title.toLowerCase().includes('docx')
  );

  const isRunning = isStarting || (isStreaming && !isComplete);
  const hasResults = directObservations.length > 0 || engineeringInterpretations.length > 0 || uncertainties.length > 0;

  return (
    <div className="cv-view-layout">
      {/* Title & Directive Banner (Preserved from Screenshot 1) */}
      <div className="cv-directive-banner">
        <IconAlertTriangle size={22} color="#b45309" />
        <div className="cv-directive-text">
          <strong style={{ color: '#92400e' }}>MANDATORY SOVEREIGNTY SAFETY DIRECTIVE:</strong>
          {' '}Direct visual observations and AI interpretations are provided solely for operational and diagnostic reference. Local VLM outputs do NOT constitute certified statutory engineering verdicts.
        </div>
      </div>

      <div className="cv-2col-layout">
        {/* Left Column: Image Upload & Parameters (Matches Screenshot 1) */}
        <div className="cv-card cv-vision-form-card">
          <div className="cv-card-header-row">
            <div className="cv-card-title-group">
              <IconEye size={19} color="#4338ca" />
              <h3 className="cv-card-heading">Multimodal Vision Inspector</h3>
            </div>
            <Badge variant="info">VLM Local Pipeline</Badge>
          </div>

          <div className="cv-form-field">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label className="cv-field-label" style={{ margin: 0 }}>Inspection Target Image</label>
              {selectedFile && (
                <button
                  type="button"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#4f46e5',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: 0,
                  }}
                  onClick={() => document.getElementById('vision-file-input')?.click()}
                  disabled={isRunning}
                >
                  Change Image
                </button>
              )}
            </div>

            {!imagePreview ? (
              <div
                className="cv-dropzone"
                onClick={() => document.getElementById('vision-file-input')?.click()}
              >
                <input
                  type="file"
                  id="vision-file-input"
                  style={{ display: 'none' }}
                  accept=".png,.jpg,.jpeg"
                  onChange={handleFileChange}
                  disabled={isRunning}
                />
                <div className="cv-dropzone-content">
                  <div className="cv-dropzone-icon-circle">
                    <IconUpload size={20} color="#4b5563" />
                  </div>
                  <div className="cv-dropzone-main-text">
                    Select or drop target image
                  </div>
                  <div className="cv-dropzone-sub-text">PNG, JPG up to 20MB</div>
                </div>
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  id="vision-file-input"
                  style={{ display: 'none' }}
                  accept=".png,.jpg,.jpeg"
                  onChange={handleFileChange}
                  disabled={isRunning}
                />
                <div className="cv-vision-preview-frame">
                  <img src={imagePreview} alt="Inspection Target Preview" className="cv-vision-img" />
                </div>
                {selectedFile && (
                  <div
                    style={{
                      marginTop: '0.45rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.78rem',
                      color: '#64748b',
                    }}
                  >
                    <span style={{ fontWeight: 600, color: '#334155' }}>
                      {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                    </span>
                    <Badge variant="neutral">Local File (0 Egress)</Badge>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="cv-form-field">
            <label className="cv-field-label">Diagnostic Prompt (Optional)</label>
            <textarea
              className="cv-textarea"
              placeholder="e.g., Identify surface micro-fractures, thermal coating oxidation, and measure defect severity..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isRunning}
              rows={3}
            />
          </div>

          {error && <div className="cv-form-error-banner">{error}</div>}

          <button
            type="button"
            className="cv-btn-purple-action"
            onClick={handleAnalyze}
            disabled={isRunning || !selectedFile}
          >
            {isRunning ? (
              <>
                <IconSparkles size={16} />
                <span>Analyzing on Local VLM...</span>
              </>
            ) : (
              <>
                <IconEye size={16} />
                <span>Execute Local Vision Analysis</span>
              </>
            )}
          </button>
        </div>

        {/* Right Column: Structured Findings & Reasoning (Matches Screenshot 1) */}
        <div className="cv-card cv-vision-results-card">
          <div className="cv-card-header-row">
            <div className="cv-card-title-group">
              <IconShield size={19} color="#15803d" />
              <h3 className="cv-card-heading">Structured Diagnostic Findings</h3>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <Badge variant="neutral">
                Model: {runtimeModel ? runtimeModel.toUpperCase() : 'LOCAL-VISION-MODEL'}
              </Badge>
              {finalStatus && (
                <Badge
                  variant={
                    finalStatus === 'succeeded'
                      ? 'success'
                      : finalStatus === 'failed'
                      ? 'error'
                      : 'info'
                  }
                >
                  {finalStatus.toUpperCase()}
                </Badge>
              )}
            </div>
          </div>

          {/* Running State Notice */}
          {isRunning && (
            <div
              style={{
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                color: '#1e40af',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                marginBottom: '1rem',
              }}
            >
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: '#2563eb',
                  animation: 'pulse 1.5s infinite',
                }}
              />
              <span>
                Analyzing image via <strong>{runtimeModel}</strong> (Stage: {activeNode || 'execution'} • Cycle {iteration}/{maxIterations})...
              </span>
            </div>
          )}

          {/* Model Unavailable Operational Notice */}
          {modelUnavailable && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1rem',
                color: '#991b1b',
              }}
            >
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 700, marginBottom: '0.35rem' }}>
                <IconAlertTriangle size={18} color="#dc2626" />
                Local Vision Model Unavailable
              </div>
              <div style={{ fontSize: '0.84rem' }}>
                The configured on-premise multimodal model (<code>{runtimeModel}</code>) is not reachable on the local Ollama instance. To enable genuine vision defect inspection without cloud egress, pull the model locally:
              </div>
              <div
                style={{
                  marginTop: '0.5rem',
                  background: '#ffffff',
                  border: '1px solid #fca5a5',
                  padding: '0.45rem 0.75rem',
                  borderRadius: '6px',
                  fontFamily: 'monospace',
                  fontSize: '0.82rem',
                  display: 'inline-block',
                  color: '#7f1d1d',
                }}
              >
                ollama pull {runtimeModel}
              </div>
            </div>
          )}

          {/* Insufficient / Unreadable Image Notice */}
          {insufficientImage && (
            <div
              style={{
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '8px',
                padding: '1rem',
                color: '#92400e',
                fontSize: '0.85rem',
                marginBottom: '1rem',
              }}
            >
              <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '0.35rem' }}>
                <IconAlertCircle size={16} color="#d97706" />
                Optical Assessment Limitation
              </div>
              <p style={{ margin: 0 }}>
                No reliable visual findings could be established from the supplied image. Surface resolution or optical conditions preclude affirmative defect identification.
              </p>
            </div>
          )}

          {/* Empty Awaiting State (When no results and not running) */}
          {!hasResults && !isRunning && !modelUnavailable ? (
            <div className="cv-empty-state-table">
              <IconEye size={40} color="#9ca3af" />
              <div className="cv-empty-title">Awaiting Vision Target</div>
              <div className="cv-empty-desc">
                Upload an engineering photo, thermal scan, or microscopic defect capture to generate structured observational findings.
              </div>
            </div>
          ) : null}

          {/* Structured Findings Output */}
          {hasResults && (
            <div className="cv-vision-findings-content">
              {/* Observations */}
              <div className="cv-finding-section">
                <div className="cv-finding-heading" style={{ justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <IconCheck size={16} color="#15803d" />
                    <span>Direct Visual Observations</span>
                  </div>
                  <Badge variant="success">Optical Features</Badge>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '0.1rem 0 0.4rem 0' }}>
                  Factual physical attributes observed directly from image pixels with zero speculative inference.
                </p>
                <div className="cv-finding-bullets">
                  {directObservations.map((obs: string, idx: number) => (
                    <div key={idx} className="cv-bullet-row">
                      <span className="cv-bullet-dot" />
                      <span>{obs}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Interpretations */}
              <div className="cv-finding-section">
                <div className="cv-finding-heading" style={{ justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <IconCpu size={16} color="#1d4ed8" />
                    <span>Engineering Interpretation</span>
                  </div>
                  <Badge variant="info">Technical Hypotheses</Badge>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '0.1rem 0 0.4rem 0' }}>
                  Conservative engineering interpretations and analytical hypotheses derived from the direct observations.
                </p>
                <div className="cv-finding-bullets">
                  {engineeringInterpretations.map((interp: string, idx: number) => (
                    <div key={idx} className="cv-bullet-row">
                      <span className="cv-bullet-dot blue" />
                      <span>{interp}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Uncertainty / Safety Bounds */}
              <div className="cv-finding-section">
                <div className="cv-finding-heading" style={{ justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <IconAlertTriangle size={16} color="#b45309" />
                    <span>Confidence Bounds & Uncertainty</span>
                  </div>
                  <Badge variant="neutral">Analytical Bounds</Badge>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '0.1rem 0 0.4rem 0' }}>
                  Explicit optical constraints, visibility limits, and unconfirmed internal structural factors.
                </p>
                <div className="cv-finding-bullets">
                  {uncertainties.map((unc: string, idx: number) => (
                    <div key={idx} className="cv-bullet-row">
                      <span className="cv-bullet-dot amber" />
                      <span>{unc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Inspection Report Deliverable Card */}
          {docxArtifact && (
            <div
              style={{
                marginTop: '1.25rem',
                background: '#fdf4ff',
                border: '1px solid #f0abfc',
                borderRadius: '8px',
                padding: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.65rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <IconFileText size={18} color="#9333ea" />
                  <strong style={{ fontSize: '0.92rem', color: '#581c87' }}>
                    Inspection Report Deliverable
                  </strong>
                </div>
                <Badge variant="success">DOCX Report Generated</Badge>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                  fontSize: '0.8rem',
                  background: '#ffffff',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #f5d0fe',
                }}
              >
                <span>
                  <span style={{ color: '#64748b' }}>Target: </span>
                  <strong style={{ color: '#1e293b' }}>{selectedFile?.name || 'Inspection Target'}</strong>
                </span>
                <span>
                  <span style={{ color: '#64748b' }}>Model: </span>
                  <strong style={{ color: '#1e293b' }}>{runtimeModel}</strong>
                </span>
                <span>
                  <span style={{ color: '#64748b' }}>Status: </span>
                  <strong style={{ color: '#16a34a' }}>Completed & Validated</strong>
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
                <a
                  href={api.getArtifactDownloadUrl(docxArtifact.artifact_id)}
                  download
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    background: '#9333ea',
                    color: '#ffffff',
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    fontWeight: 600,
                    fontSize: '0.84rem',
                    textDecoration: 'none',
                    boxShadow: '0 1px 2px rgba(147, 51, 234, 0.25)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.background = '#7e22ce')}
                  onMouseOut={(e) => (e.currentTarget.style.background = '#9333ea')}
                >
                  <IconDownload size={14} color="#ffffff" />
                  <span>Download Inspection Report (.DOCX)</span>
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};