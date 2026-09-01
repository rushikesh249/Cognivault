import React, { useEffect, useRef, useState } from 'react';
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
    <div className="cv-card cv-activity-feed-card">
      <div className="cv-card-header-row">
        <div className="cv-card-title-group">
          <IconTerminal size={18} color="#4338ca" />
          <h3 className="cv-card-heading">Real-Time Operational Activity Stream</h3>
        </div>

        <div className="cv-feed-controls">
          {reconnectCount > 0 && isStreaming && (
            <span className="cv-reconnect-badge">
              Reconnecting ({reconnectCount}/5)...
            </span>
          )}

          <select
            className="cv-select-compact"
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
          >
            <option value="all">All Events ({events.length})</option>
            <option value="info">Info only</option>
            <option value="warn">Warnings only</option>
            <option value="error">Errors only</option>
          </select>

          <button
            type="button"
            className="cv-btn-compact-secondary"
            onClick={() => setAutoScroll(!autoScroll)}
          >
            {autoScroll ? 'Lock Scroll' : 'Auto Scroll'}
          </button>
        </div>
      </div>

      <div className="cv-terminal-window" ref={terminalRef}>
        {filteredEvents.length === 0 ? (
          <div className="cv-terminal-empty">
            {isStreaming
              ? 'Connecting to Sovereign SSE stream / awaiting operational agent events...'
              : 'No activity events recorded for this task session.'}
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const timeStr = new Date(ev.ts).toLocaleTimeString();
            return (
              <div key={ev.event_id} className="cv-terminal-row">
                <span className="cv-term-ts">[{timeStr}]</span>
                <span className="cv-term-node">[{ev.node}]</span>
                <span className={`cv-term-msg ${ev.level}`}>{ev.message}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};