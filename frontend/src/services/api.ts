/**
 * REST API client for Cognivault backend.
 * Strictly uses local /api/* endpoints with zero external calls.
 */

import type {
  ArtifactMeta,
  FileUploadResult,
  HealthStatus,
  ModelListOut,
  SovereigntyStatus,
  TaskCreatePayload,
  TaskCreateResponse,
  TaskDetail,
  VisionResult,
} from '../types';

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse failure for errors
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch('/api/health');
    return handleResponse<HealthStatus>(res);
  },

  async listModels(): Promise<ModelListOut> {
    const res = await fetch('/api/models');
    return handleResponse<ModelListOut>(res);
  },

  async uploadFile(file: File, taskId?: string): Promise<FileUploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    if (taskId) {
      formData.append('task_id', taskId);
    }
    const res = await fetch('/api/files/upload', {
      method: 'POST',
      body: formData,
    });
    return handleResponse<FileUploadResult>(res);
  },

  async createTask(payload: TaskCreatePayload): Promise<TaskCreateResponse> {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<TaskCreateResponse>(res);
  },

  async getTask(taskId: string): Promise<TaskDetail> {
    const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`);
    return handleResponse<TaskDetail>(res);
  },

  async runAgent(taskId: string): Promise<{ task_id: string; status: string }> {
    const res = await fetch('/api/agent/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ task_id: taskId }),
    });
    return handleResponse<{ task_id: string; status: string }>(res);
  },

  async listArtifacts(limit = 50, offset = 0): Promise<ArtifactMeta[]> {
    const res = await fetch(`/api/artifacts?limit=${limit}&offset=${offset}`);
    return handleResponse<ArtifactMeta[]>(res);
  },

  async getArtifactMeta(artifactId: string): Promise<ArtifactMeta> {
    const res = await fetch(`/api/artifacts/${encodeURIComponent(artifactId)}?meta=true`);
    return handleResponse<ArtifactMeta>(res);
  },

  getArtifactDownloadUrl(artifactId: string): string {
    return `/api/artifacts/${encodeURIComponent(artifactId)}`;
  },

  async analyzeVision(fileId: string, prompt?: string): Promise<VisionResult> {
    const res = await fetch('/api/vision/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_id: fileId,
        ...(prompt ? { prompt } : {}),
      }),
    });
    return handleResponse<VisionResult>(res);
  },

  async getSovereigntyStatus(): Promise<SovereigntyStatus> {
    const res = await fetch('/api/sovereignty/status');
    return handleResponse<SovereigntyStatus>(res);
  },
};