import React, { useState } from 'react';
import { Badge } from '../common/Badge';
import {
  IconAlertTriangle,
  IconCheck,
  IconCpu,
  IconEye,
  IconShield,
  IconUpload,
} from '../common/Icons';
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
      setError('Please select an inspection image first.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Upload image
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
    <div className="cv-view-layout">
      {/* Title & Directive Banner */}
      <div className="cv-directive-banner">
        <IconAlertTriangle size={22} color="#b45309" />
        <div className="cv-directive-text">
          <strong style={{ color: '#92400e' }}>MANDATORY SOVEREIGNTY SAFETY DIRECTIVE:</strong>
          {' '}Direct visual observations and AI interpretations are provided solely for operational and diagnostic reference. Local VLM outputs do NOT constitute certified statutory engineering verdicts.
        </div>
      </div>

      <div className="cv-2col-layout">
        {/* Left Column: Image Upload & Parameters */}
        <div className="cv-card cv-vision-form-card">
          <div className="cv-card-header-row">
            <div className="cv-card-title-group">
              <IconEye size={19} color="#4338ca" />
              <h3 className="cv-card-heading">Multimodal Vision Inspector</h3>
            </div>
            <Badge variant="info">VLM Local Pipeline</Badge>
          </div>

          <div className="cv-form-field">
            <label className="cv-field-label">Inspection Target Image</label>
            <div
              className={`cv-dropzone ${selectedFile ? 'has-file' : ''}`}
              onClick={() => document.getElementById('vision-file-input')?.click()}
            >
              <input
                type="file"
                id="vision-file-input"
                style={{ display: 'none' }}
                accept=".png,.jpg,.jpeg"
                onChange={handleFileChange}
                disabled={loading}
              />
              <div className="cv-dropzone-content">
                <div className="cv-dropzone-icon-circle">
                  <IconUpload size={20} color="#4b5563" />
                </div>
                <div className="cv-dropzone-main-text">
                  {selectedFile ? selectedFile.name : 'Select or drop target image'}
                </div>
                <div className="cv-dropzone-sub-text">PNG, JPG up to 20MB</div>
              </div>
            </div>
          </div>

          {imagePreview && (
            <div className="cv-vision-preview-frame">
              <img src={imagePreview} alt="Inspection Preview" className="cv-vision-img" />
            </div>
          )}

          <div className="cv-form-field">
            <label className="cv-field-label">Diagnostic Prompt (Optional)</label>
            <textarea
              className="cv-textarea"
              placeholder="e.g., Identify surface micro-fractures, thermal coating oxidation, and measure defect severity..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
              rows={3}
            />
          </div>

          {error && <div className="cv-form-error-banner">{error}</div>}

          <button
            type="button"
            className="cv-btn-purple-action"
            onClick={handleAnalyze}
            disabled={loading || !selectedFile}
          >
            <IconEye size={16} />
            <span>{loading ? 'Analyzing on Local VLM...' : 'Execute Local Vision Analysis'}</span>
          </button>
        </div>

        {/* Right Column: Structured Findings & Reasoning */}
        <div className="cv-card cv-vision-results-card">
          <div className="cv-card-header-row">
            <div className="cv-card-title-group">
              <IconShield size={19} color="#15803d" />
              <h3 className="cv-card-heading">Structured Diagnostic Findings</h3>
            </div>
            {result && (
              <Badge variant="neutral">
                Model: {result.model_used || 'Local VLM'}
              </Badge>
            )}
          </div>

          {!result ? (
            <div className="cv-empty-state-table">
              <IconEye size={40} color="#9ca3af" />
              <div className="cv-empty-title">Awaiting Vision Target</div>
              <div className="cv-empty-desc">
                Upload an engineering photo, thermal scan, or microscopic defect capture to generate structured observational findings.
              </div>
            </div>
          ) : (
            <div className="cv-vision-findings-content">
              {/* Observations */}
              <div className="cv-finding-section">
                <div className="cv-finding-heading">
                  <IconCheck size={16} color="#15803d" />
                  <span>Direct Visual Observations</span>
                </div>
                <div className="cv-finding-bullets">
                  {result.observation?.map((obs: string, idx: number) => (
                    <div key={idx} className="cv-bullet-row">
                      <span className="cv-bullet-dot" />
                      <span>{obs}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Interpretations */}
              <div className="cv-finding-section">
                <div className="cv-finding-heading">
                  <IconCpu size={16} color="#1d4ed8" />
                  <span>Engineering Interpretation</span>
                </div>
                <div className="cv-finding-bullets">
                  {result.interpretation?.map((interp: string, idx: number) => (
                    <div key={idx} className="cv-bullet-row">
                      <span className="cv-bullet-dot blue" />
                      <span>{interp}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Uncertainty / Safety Bounds */}
              <div className="cv-finding-section">
                <div className="cv-finding-heading">
                  <IconAlertTriangle size={16} color="#b45309" />
                  <span>Confidence Bounds & Uncertainty</span>
                </div>
                <div className="cv-finding-bullets">
                  {result.uncertainty?.map((unc: string, idx: number) => (
                    <div key={idx} className="cv-bullet-row">
                      <span className="cv-bullet-dot amber" />
                      <span>{unc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};