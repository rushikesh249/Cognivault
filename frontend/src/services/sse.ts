/**
 * Browser-compatible SSE Stream consumer for task events.
 * Connects to GET /api/tasks/{task_id}/events.
 */

import type { TaskEvent } from '../types';

export interface SSECallbacks {
  onEvent: (event: TaskEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onTerminal?: (lastEvent: TaskEvent) => void;
}

export class TaskEventStream {
  private taskId: string;
  private callbacks: SSECallbacks;
  private eventSource: EventSource | null = null;
  private isClosed = false;

  constructor(taskId: string, callbacks: SSECallbacks) {
    this.taskId = taskId;
    this.callbacks = callbacks;
  }

  public connect(): void {
    if (this.eventSource) {
      this.close();
    }

    this.isClosed = false;
    const url = `/api/tasks/${encodeURIComponent(this.taskId)}/events`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      if (this.callbacks.onOpen) {
        this.callbacks.onOpen();
      }
    };

    this.eventSource.onmessage = (e: MessageEvent) => {
      if (this.isClosed) return;
      try {
        const data: TaskEvent = JSON.parse(e.data);
        this.callbacks.onEvent(data);

        if (data.node === 'final_deliverable') {
          if (this.callbacks.onTerminal) {
            this.callbacks.onTerminal(data);
          }
          this.close();
        }
      } catch (err) {
        console.error('Failed to parse SSE event message:', err, e.data);
      }
    };

    this.eventSource.onerror = (err) => {
      if (this.callbacks.onError && !this.isClosed) {
        this.callbacks.onError(err);
      }
    };
  }

  public close(): void {
    this.isClosed = true;
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}