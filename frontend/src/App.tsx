import React, { useState } from 'react';
import { Header } from './components/layout/Header';
import { Navigation } from './components/layout/Navigation';
import type { TabKey } from './components/layout/Navigation';
import { StatusBar } from './components/layout/StatusBar';
import { TaskCreator } from './components/agent/TaskCreator';
import { GraphVisualizer } from './components/agent/GraphVisualizer';
import { LiveEventFeed } from './components/agent/LiveEventFeed';
import { TaskSummaryCard } from './components/agent/TaskSummaryCard';
import { HeroFlowLauncher } from './components/hero/HeroFlowLauncher';
import { VisionInspector } from './components/vision/VisionInspector';
import { ArtifactExplorer } from './components/artifacts/ArtifactExplorer';
import { SovereigntyDashboard } from './components/sovereignty/SovereigntyDashboard';
import { useSovereignty } from './hooks/useSovereignty';
import { useTaskStream } from './hooks/useTaskStream';
import './styles/workbench.css';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('workspace');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  // Live telemetry hook
  const { data: sovereignty } = useSovereignty(5000);

  // Live agent execution stream hook
  const {
    events,
    activeNode,
    completedNodes,
    iteration,
    maxIterations,
    isStreaming,
    finalStatus,
    taskDetail,
    reconnectCount,
  } = useTaskStream(selectedTaskId);

  const handleTaskCreated = (taskId: string) => {
    setSelectedTaskId(taskId);
    setActiveTab('workspace');
  };

  return (
    <div className="workbench-shell">
      {/* Top Header */}
      <Header sovereignty={sovereignty} />

      {/* Main Content Area */}
      <main className="workbench-main">
        {/* Navigation Tabs */}
        <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'center' }}>
          <Navigation activeTab={activeTab} onTabChange={setActiveTab} />
        </div>

        {/* Tab 1: Agent Workbench */}
        {activeTab === 'workspace' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="grid-2col">
              <TaskCreator onTaskCreated={handleTaskCreated} disabled={isStreaming} />
              <TaskSummaryCard
                task={taskDetail}
                finalStatus={finalStatus}
                onViewArtifacts={() => setActiveTab('artifacts')}
              />
            </div>

            {/* 8-Stage Execution Visualizer */}
            <GraphVisualizer
              activeNode={activeNode}
              completedNodes={completedNodes}
              iteration={iteration}
              maxIterations={maxIterations}
              finalStatus={finalStatus}
              isStreaming={isStreaming}
            />

            {/* Real-time SSE Stream Event Feed */}
            <LiveEventFeed
              events={events}
              isStreaming={isStreaming}
              reconnectCount={reconnectCount}
            />
          </div>
        )}

        {/* Tab 2: Hero Flows Quickstart */}
        {activeTab === 'heroes' && (
          <HeroFlowLauncher
            onOpenInWorkbench={(taskId) => {
              setSelectedTaskId(taskId);
              setActiveTab('workspace');
            }}
          />
        )}

        {/* Tab 3: Multimodal Vision Inspector */}
        {activeTab === 'vision' && <VisionInspector />}

        {/* Tab 4: Sovereignty & Air-Gap Dashboard */}
        {activeTab === 'sovereignty' && <SovereigntyDashboard />}

        {/* Tab 5: Deliverables & Artifacts Catalog */}
        {activeTab === 'artifacts' && <ArtifactExplorer />}
      </main>

      {/* Bottom Live Status Bar */}
      <StatusBar
        sovereignty={sovereignty}
        activeModel={taskDetail?.model_used}
      />
    </div>
  );
};

export default App;