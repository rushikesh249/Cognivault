/**
 * React hook for live LangGraph SSE event consumption with deduplication,
 * historical replay handling, exponential reconnect backoff, and terminal detection.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { TaskEventStream } from '../services/sse';
import type { LangGraphNode, TaskDetail, TaskEvent, TaskStatus } from '../types';

export interface UseTaskStreamResult {
  events: TaskEvent[];
  activeNode: LangGraphNode | null;
  completedNodes: LangGraphNode[];
  iteration: number;
  maxIterations: number;
  isStreaming: boolean;
  isComplete: boolean;
  finalStatus: TaskStatus | null;
  taskDetail: TaskDetail | null;
  error: string | null;
  reconnectCount: number;
  refreshTask: () => Promise<void>;
  reset: () => void;
}

const ORDERED_NODES: LangGraphNode[] = [
  'task_understanding',
  'planning',
  'model_selection',
  'tool_selection',
  'execution',
  'observation',
  'validation',
  'final_deliverable',
];

export function useTaskStream(taskId: string | null): UseTaskStreamResult {
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [activeNode, setActiveNode] = useState<LangGraphNode | null>(null);
  const [completedNodes, setCompletedNodes] = useState<LangGraphNode[]>([]);
  const [iteration, setIteration] = useState<number>(1);
  const [maxIterations, setMaxIterations] = useState<number>(4);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [finalStatus, setFinalStatus] = useState<TaskStatus | null>(null);
  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reconnectCount, setReconnectCount] = useState<number>(0);

  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const streamRef = useRef<TaskEventStream | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isTerminalRef = useRef<boolean>(false);

  const reset = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    seenEventIdsRef.current.clear();
    isTerminalRef.current = false;
    setEvents([]);
    setActiveNode(null);
    setCompletedNodes([]);
    setIteration(1);
    setMaxIterations(4);
    setIsStreaming(false);
    setIsComplete(false);
    setFinalStatus(null);
    setTaskDetail(null);
    setError(null);
    setReconnectCount(0);
  }, []);

  const refreshTask = useCallback(async () => {
    if (!taskId) return;
    try {
      const detail = await api.getTask(taskId);
      setTaskDetail(detail);
      if (['succeeded', 'failed', 'failed_bounded'].includes(detail.status)) {
        setIsComplete(true);
        setFinalStatus(detail.status);
        setIsStreaming(false);
        isTerminalRef.current = true;
        if (streamRef.current) {
          streamRef.current.close();
          streamRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
          window.clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      }
    } catch (err: unknown) {
      console.warn('Failed to refresh task details:', err);
    }
  }, [taskId]);

  const processEvent = useCallback((event: TaskEvent) => {
    if (seenEventIdsRef.current.has(event.event_id)) {
      return; // Deduplicate
    }
    seenEventIdsRef.current.add(event.event_id);

    setEvents((prev) => [...prev, event]);

    const nodeName = event.node as LangGraphNode;
    if (ORDERED_NODES.includes(nodeName)) {
      setActiveNode(nodeName);
      setCompletedNodes((prev) => {
        if (!prev.includes(nodeName) && nodeName !== 'final_deliverable') {
          return [...prev, nodeName];
        }
        return prev;
      });
    }

    // Inspect messages for iteration counters e.g., 'Iteration 2/6'
    const iterMatch = event.message.match(/iteration\s*(\d+)(?:\/(\d+))?/i);
    if (iterMatch) {
      const current = parseInt(iterMatch[1], 10);
      if (!isNaN(current)) setIteration(current);
      if (iterMatch[2]) {
        const max = parseInt(iterMatch[2], 10);
        if (!isNaN(max)) setMaxIterations(max);
      }
    }

    // Handle terminal status message
    if (nodeName === 'final_deliverable') {
      isTerminalRef.current = true;
      setIsStreaming(false);
      setIsComplete(true);
      if (streamRef.current) {
        streamRef.current.close();
        streamRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (event.message.includes("status='succeeded'")) {
        setFinalStatus('succeeded');
      } else if (event.message.includes("status='failed_bounded'")) {
        setFinalStatus('failed_bounded');
      } else if (event.message.includes("status='failed'")) {
        setFinalStatus('failed');
      }
    }
  }, []);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    setIsStreaming(true);
    let attempts = 0;

    const connectStream = () => {
      if (isTerminalRef.current) return;

      const stream = new TaskEventStream(taskId, {
        onOpen: () => {
          setIsStreaming(true);
          setError(null);
        },
        onEvent: (ev) => {
          processEvent(ev);
        },
        onTerminal: () => {
          setIsStreaming(false);
          setIsComplete(true);
          isTerminalRef.current = true;
          if (streamRef.current) {
            streamRef.current.close();
            streamRef.current = null;
          }
          if (reconnectTimeoutRef.current) {
            window.clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
          void refreshTask();
        },
        onError: () => {
          if (isTerminalRef.current) return;

          // Attempt bounded exponential backoff only if not terminal
          if (attempts < 5) {
            attempts += 1;
            setReconnectCount(attempts);
            const delay = Math.min(1000 * Math.pow(2, attempts - 1), 8000);
            reconnectTimeoutRef.current = window.setTimeout(() => {
              if (!isTerminalRef.current) {
                connectStream();
              }
            }, delay);
          } else {
            setIsStreaming(false);
            if (!isTerminalRef.current) {
              setError('Connection lost to event stream. Switched to periodic status check.');
              void refreshTask();
            }
          }
        },
      });

      streamRef.current = stream;
      stream.connect();
    };

    // Initial load: fetch task details then connect SSE
    void refreshTask().then(() => {
      connectStream();
    });

    return () => {
      if (streamRef.current) {
        streamRef.current.close();
        streamRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [taskId, processEvent, refreshTask]);

  return {
    events,
    activeNode,
    completedNodes,
    iteration,
    maxIterations,
    isStreaming,
    isComplete,
    finalStatus,
    taskDetail,
    error,
    reconnectCount,
    refreshTask,
    reset,
  };
}