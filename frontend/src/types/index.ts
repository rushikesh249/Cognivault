/**
 * Type definitions for Cognivault: Sovereign On-Premise Agentic AI Workbench
 * Aligned strictly with backend Pydantic models (TRD Phase 0-12).
 */

export type TaskType = 'document' | 'coding' | 'vision';

export type TaskStatus = 'created' | 'running' | 'succeeded' | 'failed' | 'failed_bounded';

export type LangGraphNode =
  | 'task_understanding'
  | 'planning'
  | 'model_selection'
  | 'tool_selection'
  | 'execution'
  | 'observation'
  | 'validation'
  | 'final_deliverable';

export type EventLevel = 'info' | 'warn' | 'error';

export interface TaskEvent {
  event_id: string;
  task_id: string;
  node: LangGraphNode | string;
  message: string;
  level: EventLevel;
  ts: string;
}

export interface TaskCreatePayload {
  title: string;
  task_type: TaskType;
  prompt: string;
  file_ids?: string[];
}

export interface TaskCreateResponse {
  task_id: string;
  status: string;
  created_at: string;
}

export interface TaskDetail {
  task_id: string;
  title: string;
  task_type: TaskType;
  prompt: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  artifact_ids: string[];
  model_used: string | null;
}

export interface AgentRunResponse {
  task_id: string;
  status: string;
}

export interface ArtifactMeta {
  artifact_id: string;
  task_id: string;
  kind: string;
  title: string;
  sources: string[];
  created_at: string;
}

export interface VisionResult {
  observation: string[];
  interpretation: string[];
  uncertainty: string[];
  model_used: string;
}

export interface SovereigntyStatus {
  external_ai_calls: number;
  external_embedding_calls: number;
  external_ocr_calls: number;
  data_egress_mb: number;
  local_inference: 'ok' | 'degraded';
  local_ocr: 'ok' | 'degraded';
  local_rag: 'ok' | 'degraded';
  local_vision: 'ok' | 'degraded';
  local_sandbox: 'ok' | 'degraded';
  monitor_status: 'ok' | 'degraded';
  byte_accounting_supported: boolean;
  external_connections_5m: number;
  external_dns_lookups_5m: number;
}

export interface ModelInfo {
  model_id: string;
  display_name: string;
  role: string;
  capabilities: string[];
  modalities: string[];
  context_length: number;
  vram_gb: number;
  serving_backend: string;
  model_path: string;
  enabled: boolean;
  available: boolean;
  status: string;
  provider_status: string;
}

export interface ModelListOut {
  models: ModelInfo[];
}

export interface FileUploadResult {
  file_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  chunk_count: number;
  ocr_applied: boolean;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
}