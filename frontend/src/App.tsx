import React, { useEffect, useState } from 'react';
import './App.css';

interface HealthStatus {
  status: string;
  app: string;
  version: string;
}

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! Status: ${res.status}`);
        }
        return res.json();
      })
      .then((data: HealthStatus) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0f172a',
      color: '#f8fafc',
      fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem'
    }}>
      <div style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '2.5rem',
        maxWidth: '540px',
        width: '100%',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)'
      }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: '0 0 0.5rem 0', color: '#38bdf8' }}>
          Sovereign AI Workbench
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '0.875rem', margin: '0 0 1.5rem 0' }}>
          Phase 0 — Environment & Repository Foundation
        </p>

        <div style={{
          backgroundColor: '#0f172a',
          borderRadius: '6px',
          padding: '1rem',
          border: '1px solid #1e293b',
          fontSize: '0.875rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ color: '#64748b' }}>Backend Status:</span>
            <span>
              {loading && <span style={{ color: '#eab308' }}>Probing backend...</span>}
              {error && <span style={{ color: '#ef4444' }}>Offline ({error})</span>}
              {health && <span style={{ color: '#22c55e' }}>● {health.status.toUpperCase()}</span>}
            </span>
          </div>
          {health && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ color: '#64748b' }}>App:</span>
                <span style={{ color: '#f1f5f9' }}>{health.app}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Version:</span>
                <span style={{ color: '#f1f5f9' }}>{health.version}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
