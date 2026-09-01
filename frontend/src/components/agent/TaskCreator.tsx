import React, { useState } from 'react';
import { IconPlay, IconUpload } from '../common/Icons';
import { api } from '../../services/api';
import type { TaskCreatePayload, TaskType } from '../../types';

interface TaskCreatorProps {
  onTaskCreated: (taskId: string) => void;
  disabled?: boolean;
}

export const TaskCreator: React.FC<TaskCreatorProps> = ({ onTaskCreated, disabled = false }) => {
  const [taskCategory, setTaskCategory] = useState<TaskType>('document');
  const [title, setTitle] = useState<string>('');
  const [prompt, setPrompt] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError('Instructions for the agent cannot be empty.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let fileIds: string[] = [];

      // 1. If file attached, upload first
      if (selectedFile) {
        if (selectedFile.size > 50 * 1024 * 1024) {
          throw new Error('Attached file exceeds 50 MB limit.');
        }
        const uploadRes = await api.uploadFile(selectedFile);
        fileIds = [uploadRes.file_id];
      }

      // 2. Create task
      const payload: TaskCreatePayload = {
        title: title.trim() || `${taskCategory.toUpperCase()} Task - ${new Date().toLocaleTimeString()}`,
        task_type: taskCategory,
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

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled || loading) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      const fn = file.name.toLowerCase();
      if (fn.endsWith('.jpg') || fn.endsWith('.jpeg') || fn.endsWith('.png')) {
        setTaskCategory('vision');
      }
    }
  };

  return (
    <div className="cv-card cv-task-configure-card">
      <form onSubmit={handleSubmit} className="cv-task-form">
        {/* 1. Task Category Segmented Control */}
        <div className="cv-form-field">
          <label className="cv-field-label">Task Category</label>
          <div className="cv-segmented-control">
            <button
              type="button"
              className={`cv-segment-btn ${taskCategory === 'document' ? 'active' : ''}`}
              onClick={() => setTaskCategory('document')}
            >
              Document
            </button>
            <button
              type="button"
              className={`cv-segment-btn ${taskCategory === 'coding' ? 'active' : ''}`}
              onClick={() => setTaskCategory('coding')}
            >
              Code
            </button>
            <button
              type="button"
              className={`cv-segment-btn ${taskCategory === 'vision' ? 'active' : ''}`}
              onClick={() => setTaskCategory('vision')}
            >
              Vision
            </button>
          </div>
        </div>

        {/* 2. Task Title Input */}
        <div className="cv-form-field">
          <label className="cv-field-label">Task Title</label>
          <input
            type="text"
            className="cv-input-text"
            placeholder="e.g., Analyze Q3 Financial Reports"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={disabled || loading}
          />
        </div>

        {/* 3. Instructions Textarea */}
        <div className="cv-form-field">
          <div className="cv-field-label-row">
            <label className="cv-field-label">Instructions</label>
            <div className="cv-preset-links">
              <button
                type="button"
                className="cv-mini-preset-btn"
                onClick={() => {
                  setTaskCategory('document');
                  setTitle('Analyze Turbine Rotor Inspection Report');
                  setPrompt('Extract findings and anomalies from inspection report, search safety standards in knowledge base, evaluate compliance gaps, and generate technical structured analysis report DOCX artifact.');
                }}
              >
                Sample Doc
              </button>
              <button
                type="button"
                className="cv-mini-preset-btn"
                onClick={() => {
                  setTaskCategory('coding');
                  setTitle('Factorial Algorithm with Self-Correction');
                  setPrompt('Write a python factorial function with unit tests in Docker sandbox. If tests fail, inspect stderr and self-correct.');
                }}
              >
                Sample Code
              </button>
            </div>
          </div>
          <textarea
            className="cv-textarea"
            placeholder="Provide detailed instructions for the agent..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={disabled || loading}
            rows={4}
          />
        </div>

        {/* 4. Attachment Drag-and-Drop Dropzone */}
        <div className="cv-form-field">
          <label className="cv-field-label">Attachment</label>
          <div
            className={`cv-dropzone ${selectedFile ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => document.getElementById('task-file-input')?.click()}
          >
            <input
              type="file"
              id="task-file-input"
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  const file = e.target.files[0];
                  setSelectedFile(file);
                  const fn = file.name.toLowerCase();
                  if (fn.endsWith('.jpg') || fn.endsWith('.jpeg') || fn.endsWith('.png')) {
                    setTaskCategory('vision');
                  }
                }
              }}
              disabled={disabled || loading}
            />

            <div className="cv-dropzone-content">
              <div className="cv-dropzone-icon-circle">
                <IconUpload size={20} color="#4b5563" />
              </div>
              <div className="cv-dropzone-main-text">
                {selectedFile ? (
                  <span style={{ color: '#111827', fontWeight: 600 }}>{selectedFile.name}</span>
                ) : (
                  'Click or drag files to upload'
                )}
              </div>
              <div className="cv-dropzone-sub-text">
                {selectedFile
                  ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB attached`
                  : 'PDF, DOCX, TXT up to 50MB'}
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="cv-form-error-banner">
            {error}
          </div>
        )}

        {/* Launch Run Button (Bottom Right) */}
        <div className="cv-form-actions-row">
          <button
            type="submit"
            className="cv-btn-purple-action cv-btn-launch"
            disabled={disabled || loading || !prompt.trim()}
            id="btn-launch-run"
          >
            <span>{loading ? 'Initializing Agent...' : 'Launch run'}</span>
            <IconPlay size={16} />
          </button>
        </div>
      </form>
    </div>
  );
};