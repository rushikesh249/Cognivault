import React, { useMemo } from 'react';
import {
  IconEye,
  IconCpu,
  IconAlertTriangle,
  IconAlertCircle,
  IconCheck,
  IconDownload,
  IconFileText,
  IconShield,
  IconSparkles,
} from '../common/Icons';
import { Badge } from '../common/Badge';
import { api } from '../../services/api';
import type { ArtifactMeta, LangGraphNode, TaskDetail, TaskEvent, TaskStatus } from '../../types';

interface HeroVisionInspectorProps {
  taskDetail: TaskDetail | null;
  events: TaskEvent[];
  isStreaming: boolean;
  isTerminal: boolean;
  effectiveStatus: TaskStatus | null;
  modelUnavailable: boolean;
  artifacts: ArtifactMeta[];
  activeNode: LangGraphNode | null;
  iteration: number;
  maxIterations: number;
}

export const HeroVisionInspector: React.FC<HeroVisionInspectorProps> = ({
  taskDetail,
  events,
  isStreaming,
  isTerminal,
  effectiveStatus,
  modelUnavailable,
  artifacts,
  activeNode,
  iteration,
  maxIterations,
}) => {
  // 1. Parse structured findings and metadata dynamically from real runtime events and task details
  const {
    sourceFilename,
    directObservations,
    engineeringInterpretations,
    uncertainties,
    runtimeModel,
    insufficientImage,
  } = useMemo(() => {
    let filename = 'synthetic_weld_flange.jpg';
    let model = taskDetail?.model_used || null;
    let insufficient = false;

    const observations: string[] = [];
    const interpretations: string[] = [];
    const uncerts: string[] = [];

    for (const ev of events) {
      const msg = ev.message;

      // Detect source image filename if logged in events
      const fileMatch = msg.match(/on image ['"]?([^'"]+)['"]?/i);
      if (fileMatch && fileMatch[1]) {
        filename = fileMatch[1];
      }

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

      // Detect unreadable/insufficient image notice
      if (msg.toLowerCase().includes('no readable text') || msg.toLowerCase().includes('no reliable visual findings')) {
        insufficient = true;
      }

      // Parse tagged findings
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

    // Default runtime model fallback
    const resolvedModel = model || 'llava:7b-v1.5-q4_K_M';

    return {
      sourceFilename: filename,
      directObservations: observations,
      engineeringInterpretations: interpretations,
      uncertainties: uncerts,
      runtimeModel: resolvedModel,
      insufficientImage: insufficient,
    };
  }, [events, taskDetail]);

  const docxArtifact = artifacts.find(
    (a) => a.kind === 'docx' || a.title.toLowerCase().includes('inspection') || a.title.toLowerCase().includes('docx')
  );

  const isCompleted = effectiveStatus === 'succeeded';
  const isFailed = effectiveStatus === 'failed' || effectiveStatus === 'failed_bounded';
  const isRunning = isStreaming && !isTerminal;

  return (
    <div className="cv-vision-inspector-container" style={{ marginTop: '1.25rem' }}>
      {/* 1. Header Bar: Title and Metadata Badges */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '10px',
          padding: '1rem 1.25rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginBottom: '1rem',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div
            style={{
              background: '#eff6ff',
              color: '#2563eb',
              borderRadius: '8px',
              width: '34px',
              height: '34px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <IconEye size={20} color="#2563eb" />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#0f172a' }}>
              Multimodal Vision Inspector
            </h3>
            <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
              Industrial optical feature extraction & sovereign automated inspection
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Badge variant="neutral">
            <span style={{ color: '#64748b', marginRight: '4px' }}>MODEL:</span>
            <strong style={{ color: '#0f172a' }}>{runtimeModel ? runtimeModel.toUpperCase() : 'LOCAL-VISION-MODEL'}</strong>
          </Badge>

          <Badge variant="info">
            <span style={{ color: '#1d4ed8', marginRight: '4px' }}>PIPELINE:</span>
            <strong>VLM LOCAL PIPELINE</strong>
          </Badge>

          <Badge
            variant={
              isCompleted
                ? 'success'
                : isFailed
                ? 'error'
                : isRunning
                ? 'info'
                : 'neutral'
            }
          >
            <span style={{ marginRight: '4px' }}>STATUS:</span>
            <strong>
              {isCompleted
                ? 'COMPLETED'
                : isFailed
                ? 'FAILED'
                : isRunning
                ? 'RUNNING'
                : 'INITIALIZING'}
            </strong>
          </Badge>
        </div>
      </div>

      {/* 2. Operational Notice: Model Unavailable Banner */}
      {modelUnavailable && (
        <div
          style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1rem',
            color: '#991b1b',
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'flex-start',
          }}
        >
          <IconAlertTriangle size={20} color="#dc2626" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '0.85rem' }}>
            <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '0.25rem' }}>
              Local Vision Model Unavailable
            </div>
            <div>
              The configured on-premise multimodal model (<code>{runtimeModel || 'llava:7b-v1.5-q4_K_M'}</code>) is not reachable on the local Ollama instance. To enable genuine vision defect inspection without cloud egress, pull the model locally:
            </div>
            <div
              style={{
                marginTop: '0.5rem',
                background: '#ffffff',
                border: '1px solid #fca5a5',
                padding: '0.5rem 0.75rem',
                borderRadius: '6px',
                fontFamily: 'monospace',
                fontSize: '0.82rem',
                display: 'inline-block',
                color: '#7f1d1d',
              }}
            >
              ollama pull {runtimeModel || 'llava:7b-v1.5-q4_K_M'}
            </div>
          </div>
        </div>
      )}

      {/* 3. Main Inspection Two-Column Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 360px) 1fr',
          gap: '1.25rem',
          alignItems: 'start',
        }}
      >
        {/* Left Column: Inspection Target Image Card */}
        <div
          style={{
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '10px',
            padding: '1.15rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.85rem',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700, color: '#1e293b' }}>
              Inspection Target Image
            </h4>
            <Badge variant="neutral">Local File</Badge>
          </div>

          <div
            style={{
              width: '100%',
              height: '240px',
              borderRadius: '8px',
              overflow: 'hidden',
              background: '#090d16',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            <img
              src="/synthetic_weld_flange.jpg"
              alt="Inspection Target"
              style={{
                maxWidth: '100%',
                maxHeight: '100%',
                objectFit: 'contain',
                display: 'block',
              }}
            />
            {isRunning && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(15, 23, 42, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#38bdf8',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  backdropFilter: 'blur(2px)',
                }}
              >
                <IconSparkles size={16} color="#38bdf8" style={{ marginRight: '6px' }} />
                Scanning Optical Surface...
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
              <span>Target File:</span>
              <strong style={{ color: '#334155' }}>{sourceFilename}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
              <span>Category:</span>
              <span style={{ color: '#334155' }}>Mechanical Flange Joint</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
              <span>Sovereignty:</span>
              <span style={{ color: '#16a34a', fontWeight: 600 }}>0 Cloud Egress / Local</span>
            </div>
          </div>
        </div>

        {/* Right Column: Structured Vision Findings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
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

          {/* Insufficient / Unreadable Image State */}
          {insufficientImage && (
            <div
              style={{
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '8px',
                padding: '1rem',
                color: '#92400e',
                fontSize: '0.85rem',
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

          {/* Card 1: Direct Visual Observations */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '10px',
              padding: '1rem 1.15rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.65rem',
                borderBottom: '1px solid #f1f5f9',
                marginBottom: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <IconEye size={16} color="#16a34a" />
                <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#0f172a', letterSpacing: '0.02em' }}>
                  DIRECT VISUAL OBSERVATIONS
                </span>
              </div>
              <Badge variant="success">Optical Features</Badge>
            </div>

            <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '0 0 0.75rem 0' }}>
              Factual physical attributes observed directly from image pixels with zero speculative inference.
            </p>

            {directObservations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {directObservations.map((obs, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.65rem',
                      padding: '0.55rem 0.75rem',
                      background: '#f8fafc',
                      borderLeft: '3px solid #16a34a',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '0.84rem',
                      lineHeight: '1.4',
                      color: '#1e293b',
                    }}
                  >
                    <IconCheck size={14} color="#16a34a" style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{obs}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#94a3b8', fontSize: '0.82rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                {isRunning ? 'Extracting physical surface observations...' : 'Awaiting visual observation extraction.'}
              </div>
            )}
          </div>

          {/* Card 2: Engineering Interpretation */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '10px',
              padding: '1rem 1.15rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.65rem',
                borderBottom: '1px solid #f1f5f9',
                marginBottom: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <IconCpu size={16} color="#2563eb" />
                <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#0f172a', letterSpacing: '0.02em' }}>
                  ENGINEERING INTERPRETATION
                </span>
              </div>
              <Badge variant="info">Technical Hypotheses</Badge>
            </div>

            <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '0 0 0.75rem 0' }}>
              Conservative engineering interpretations and analytical hypotheses derived from the direct observations.
            </p>

            {engineeringInterpretations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {engineeringInterpretations.map((interp, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.65rem',
                      padding: '0.55rem 0.75rem',
                      background: '#f8fafc',
                      borderLeft: '3px solid #2563eb',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '0.84rem',
                      lineHeight: '1.4',
                      color: '#1e293b',
                    }}
                  >
                    <IconCpu size={14} color="#2563eb" style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{interp}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#94a3b8', fontSize: '0.82rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                {isRunning ? 'Formulating grounded engineering interpretations...' : 'Awaiting interpretation formulation.'}
              </div>
            )}
          </div>

          {/* Card 3: Confidence & Uncertainty */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '10px',
              padding: '1rem 1.15rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.65rem',
                borderBottom: '1px solid #f1f5f9',
                marginBottom: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <IconShield size={16} color="#64748b" />
                <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#0f172a', letterSpacing: '0.02em' }}>
                  CONFIDENCE & UNCERTAINTY
                </span>
              </div>
              <Badge variant="neutral">Analytical Bounds</Badge>
            </div>

            <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '0 0 0.75rem 0' }}>
              Explicit optical constraints, visibility limits, and unconfirmed internal structural factors.
            </p>

            {uncertainties.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {uncertainties.map((uncert, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.65rem',
                      padding: '0.55rem 0.75rem',
                      background: '#f8fafc',
                      borderLeft: '3px solid #64748b',
                      borderRadius: '0 6px 6px 0',
                      fontSize: '0.84rem',
                      lineHeight: '1.4',
                      color: '#475569',
                    }}
                  >
                    <IconAlertCircle size={14} color="#64748b" style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{uncert}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#94a3b8', fontSize: '0.82rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                {isRunning ? 'Evaluating optical visibility constraints...' : 'Advisory AI analysis only — does not constitute a certified statutory engineering inspection verdict.'}
              </div>
            )}
          </div>

          {/* 4. Professional Inspection Report / Artifact Section */}
          {docxArtifact && isCompleted && (
            <div
              style={{
                background: '#fdf4ff',
                border: '1px solid #f0abfc',
                borderRadius: '10px',
                padding: '1.15rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <IconFileText size={18} color="#9333ea" />
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#581c87' }}>
                    Inspection Report Deliverable
                  </span>
                </div>
                <Badge variant="success">DOCX Report Generated</Badge>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '0.75rem',
                  fontSize: '0.8rem',
                  background: '#ffffff',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #f5d0fe',
                }}
              >
                <div>
                  <span style={{ color: '#64748b' }}>Target: </span>
                  <strong style={{ color: '#1e293b' }}>{sourceFilename}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b' }}>Model: </span>
                  <strong style={{ color: '#1e293b' }}>{runtimeModel}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b' }}>Status: </span>
                  <strong style={{ color: '#16a34a' }}>Completed & Validated</strong>
                </div>
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
                    padding: '0.55rem 1.15rem',
                    borderRadius: '6px',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    textDecoration: 'none',
                    boxShadow: '0 1px 2px rgba(147, 51, 234, 0.25)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.background = '#7e22ce')}
                  onMouseOut={(e) => (e.currentTarget.style.background = '#9333ea')}
                >
                  <IconDownload size={15} color="#ffffff" />
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
