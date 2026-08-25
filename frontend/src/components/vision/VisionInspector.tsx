import React, { useState } from 'react';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { IconAlertTriangle, IconCheck, IconCpu, IconEye, IconInfo, IconUpload } from '../common/Icons';
import { api } from '../../services/api';
import type { VisionResult } from '../../types';

export const VisionInspector: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<VisionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
      setResult(null);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select an image file first.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Upload image to get file_id
      const uploadRes = await api.uploadFile(selectedFile);

      // 2. Direct vision analysis endpoint
      const visionRes = await api.analyzeVision(uploadRes.file_id, prompt.trim() || undefined);
      setResult(visionRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Vision analysis failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Safety Disclaimer Banner */}
      <div style={{
        padding: '0.85rem 1.25rem',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        border: '1px solid rgba(245, 158, 11, 0.3)',
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        color: '#f8fafc'
      }}>
        <IconAlertTriangle size={22} color="#f59e0b" />
        <div style={{ fontSize: '0.825rem' }}>
          <strong style={{ color: '#f59e0b' }}>MANDATORY SOVEREIGNTY SAFETY DIRECTIVE:</strong>
          {' '}Direct visual observations and AI interpretations are provided solely for informational and diagnostic reference. Local VLM outputs do NOT constitute certified engineering inspection verdicts or statutory guarantees.
        </div>
      </div>

      <div className="grid-2col">
        {/* Upload & Controls */}
        <Card title="Multimodal Image Inspector (POST /api/vision/analyze)" icon={<IconEye size={18} color="#38bdf8" />}>
          <div className="form-group">
            <label className="form-label">Inspection Image</label>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="file"
                id="vision-file-upload"
                style={{ display: 'none' }}
                accept=".jpg,.jpeg,.png"
                onChange={handleFileChange}
                disabled={loading}
              />
              <label htmlFor="vision-file-upload" className="btn btn-secondary" style={{ cursor: loading ? 'not-allowed' : 'pointer' }}>
                <IconUpload size={14} />
                {selectedFile ? 'Change Image' : 'Select Equipment Photo'}
              </label>
              {selectedFile && (
                <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                  {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                </span>
              )}
            </div>
          </div>

          {imagePreview && (
            <div style={{
              margin: '0.75rem 0',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--border-default)',
              maxHeight: '260px',
              display: 'flex',
              justifyContent: 'center',
              backgroundColor: '#000'
            }}>
              <img
                src={imagePreview}
                alt="Inspection Target"
                style={{ maxWidth: '100%', maxHeight: '260px', objectFit: 'contain' }}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Custom Inspection Prompt (Optional)</label>
            <textarea
              className="form-textarea"
              placeholder="e.g., Detail visible wear patterns, surface corrosion, pitting, and thermal discoloration..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
              rows={3}
            />
          </div>

          {error && (
            <div style={{
              padding: '0.6rem 0.85rem',
              backgroundColor: 'var(--status-error-bg)',
              border: '1px solid var(--status-error-border)',
              borderRadius: '6px',
              color: 'var(--status-error)',
              fontSize: '0.8rem',
              marginBottom: '1rem'
            }}>
              {error}
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem' }}
            onClick={handleAnalyze}
            disabled={loading || !selectedFile}
          >
            <IconEye size={16} />
            {loading ? 'Running Local VLM Inference...' : 'Analyze Equipment Image'}
          </button>
        </Card>

        {/* Structured Findings Output */}
        <Card
          title="Structured Vision Findings"
          icon={<IconInfo size={18} color="#38bdf8" />}
          badge={
            result ? (
              <Badge variant="info" icon={<IconCpu size={12} />}>
                Model: {result.model_used}
              </Badge>
            ) : null
          }
        >
          {!result ? (
            <div style={{
              color: '#64748b',
              textAlign: 'center',
              padding: '4rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <IconEye size={36} color="#334155" />
              <span>Select an image and click analyze to view structured observations, interpretations, and uncertainty caveats.</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Observations */}
              <div style={{
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: '8px',
                padding: '0.85rem'
              }}>
                <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#10b981', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <IconCheck size={14} /> Factual Visual Observations ({result.observation.length})
                </div>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.8rem', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {result.observation.map((obs, idx) => (
                    <li key={idx}>{obs}</li>
                  ))}
                </ul>
              </div>

              {/* Interpretations */}
              <div style={{
                backgroundColor: 'rgba(56, 189, 248, 0.08)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                borderRadius: '8px',
                padding: '0.85rem'
              }}>
                <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <IconInfo size={14} /> AI Engineering Interpretations ({result.interpretation.length})
                </div>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.8rem', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {result.interpretation.map((interp, idx) => (
                    <li key={idx}>{interp}</li>
                  ))}
                </ul>
              </div>

              {/* Uncertainties */}
              <div style={{
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: '8px',
                padding: '0.85rem'
              }}>
                <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#f59e0b', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <IconAlertTriangle size={14} /> Uncertainties & Limitations ({result.uncertainty.length})
                </div>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.8rem', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {result.uncertainty.map((uncert, idx) => (
                    <li key={idx}>{uncert}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};