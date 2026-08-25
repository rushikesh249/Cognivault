import React, { useEffect, useRef, useState } from 'react';
import { Card } from '../common/Card';
import { IconTerminal } from '../common/Icons';
import type { TaskEvent } from '../../types';

interface LiveEventFeedProps {
  events: TaskEvent[];
  isStreaming: boolean;
  reconnectCount: number;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({ events, isStreaming, reconnectCount }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [filterLevel, setFilterLevel] = useState<string>('all');

  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const filteredEvents = events.filter((ev) => {
    if (filterLevel === 'all') return true;
    return ev.level === filterLevel;
  });

  return (
    <Card
      title="Real-Time Event Stream (SSE Replay & Live)"
      icon={<IconTerminal size={18} color="#38bdf8" />}
      badge={
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {reconnectCount > 0 && isStreaming && (
            <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>
              Reconnecting (attempt {reconnectCount}/5)...
            </span>
          )}
          <select
            className="form-select"
            style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
          >
            <option value="all">All Levels ({events.length})</option>
            <option value="info">Info only</option>
            <option value="warn">Warnings only</option>
            <option value="error">Errors only</option>
          </select>
          <button
            type="button"
            className={`btn btn-secondary`}
            style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setAutoScroll(!autoScroll)}
          >
            {autoScroll ? 'Lock Scroll' : 'Auto Scroll'}
          </button>
        </div>
      }
    >
      <div className="event-terminal" ref={terminalRef}>
        {filteredEvents.length === 0 ? (
          <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem 0' }}>
            {isStreaming ? 'Connecting to SSE stream / awaiting agent events...' : 'No events logged for this task.'}
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const timeStr = new Date(ev.ts).toLocaleTimeString();
            return (
              <div key={ev.event_id} className="event-row">
                <span className="event-ts">[{timeStr}]</span>
                <span className="event-node">[{ev.node}]</span>
                <span className={`event-msg ${ev.level}`}>{ev.message}</span>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
};