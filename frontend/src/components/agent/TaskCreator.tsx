import React, { useState } from 'react';
import { Card } from '../common/Card';
import { IconCode, IconCpu, IconEye, IconFileText, IconPlay, IconUpload } from '../common/Icons';
import { api } from '../../services/api';
import type { TaskCreatePayload, TaskType } from '../../types';

interface TaskCreatorProps {
  onTaskCreated: (taskId: string) => void;
  disabled?: boolean;
}

export const TaskCreator: React.FC<TaskCreatorProps> = ({ onTaskCreated, disabled = false }) => {
  const [title, setTitle] = useState<string>('');
  const [taskType, setTaskType] = useState<TaskType>('document');
  const [prompt, setPrompt] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError('Task prompt / instructions cannot be empty.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let fileIds: string[] = [];

      // 1. If file attached, upload first
      if (selectedFile) {
        if (selectedFile.size > 10 * 1024 * 1024) {
          throw new Error('Attached file exceeds 10 MB limit.');
        }
        const uploadRes = await api.uploadFile(selectedFile);
        fileIds = [uploadRes.file_id];
      }

      // 2. Create task
      const payload: TaskCreatePayload = {
        title: title.trim() || `${taskType.toUpperCase()} Task - ${new Date().toLocaleTimeString()}`,
        task_type: taskType,
        prompt: prompt.trim(),
        file_ids: fileIds,
      };

      const taskRes = await api.createTask(payload);

      // 3. Launch agent execution
      await api.runAgent(taskRes.task_id);

      onTaskCreated(taskRes.task_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch agent task';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handlePreset = (type: TaskType, presetTitle: string, presetPrompt: string) => {
    setTaskType(type);
    setTitle(presetTitle);
    setPrompt(presetPrompt);
  };

  return (
    <Card title="Configure & Launch Sovereign Agent" icon={<IconCpu size={18} color="#38bdf8" />}>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Task Category</label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
            <button
              type="button"
              className={`btn ${taskType === 'document' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTaskType('document')}
            >
              <IconFileText size={15} />
              Document RAG
            </button>
            <button
              type="button"
              className={`btn ${taskType === 'coding' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTaskType('coding')}
            >
              <IconCode size={15} />
              Coding & Docker
            </button>
            <button
              type="button"
              className={`btn ${taskType === 'vision' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTaskType('vision')}
            >
              <IconEye size={15} />
              Multimodal Vision
            </button>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Task Title (Optional)</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., Turbine Rotor Blade Inspection Analysis"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={disabled || loading}
          />
        </div>

        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label className="form-label">Instructions & Goal</label>
            <div style={{ display: 'flex', gap: '0.35rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.15rem 0.4rem', fontSize: '0.7rem' }}
                onClick={() =>
                  handlePreset(
                    'document',
                    'Turbine Blade Inspection Report',
                    'Extract findings from inspection report, evaluate compliance gaps against ISO standards in knowledge base, and generate technical Approval Note DOCX artifact.'
                  )
                }
              >
                Doc Preset
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '0.15rem 0.4rem', fontSize: '0.7rem' }}
                onClick={() =>
                  handlePreset(
                    'coding',
                    'Factorial Algorithm Implementation',
                    'Write a python factorial function with unit tests in Docker sandbox. If tests fail, inspect stderr and self-correct.'
                  )
                }
              >
                Code Preset
              </button>
            </div>
          </div>
          <textarea
            className="form-textarea"
            placeholder="Describe the objective, target artifact formats (DOCX, XLSX, PPTX, PDF), and specific requirements..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={disabled || loading}
            rows={4}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Attach File / Image (Optional, max 10MB)</label>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="file"
              id="file-upload"
              style={{ display: 'none' }}
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                }
              }}
              disabled={disabled || loading}
            />
            <label
              htmlFor="file-upload"
              className="btn btn-secondary"
              style={{ cursor: disabled || loading ? 'not-allowed' : 'pointer' }}
            >
              <IconUpload size={14} />
              {selectedFile ? 'Change File' : 'Browse File'}
            </label>
            {selectedFile && (
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>
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
          type="submit"
          className="btn btn-primary"
          style={{ width: '100%', padding: '0.75rem' }}
          disabled={disabled || loading || !prompt.trim()}
        >
          <IconPlay size={16} />
          {loading ? 'Submitting & Initializing Agent...' : 'Launch Sovereign Agent Run'}
        </button>
      </form>
    </Card>
  );
};