import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import type { NavItemKey } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { PerimeterBanner } from './components/layout/PerimeterBanner';
import { OverviewView } from './components/layout/OverviewView';
import { ModelsView } from './components/layout/ModelsView';
import { ToolsView } from './components/layout/ToolsView';
import { GovernanceView } from './components/layout/GovernanceView';
import { TaskCreator } from './components/agent/TaskCreator';
import { WorkbenchSidePanels } from './components/agent/WorkbenchSidePanels';
import { GraphVisualizer } from './components/agent/GraphVisualizer';
import { LiveEventFeed } from './components/agent/LiveEventFeed';
import { TaskSummaryCard } from './components/agent/TaskSummaryCard';
import { HeroFlowLauncher } from './components/hero/HeroFlowLauncher';
import { VisionInspector } from './components/vision/VisionInspector';
import { ArtifactExplorer } from './components/artifacts/ArtifactExplorer';
import { SovereigntyDashboard } from './components/sovereignty/SovereigntyDashboard';
import { useSovereignty } from './hooks/useSovereignty';
import { useTaskStream } from './hooks/useTaskStream';
import type { TaskDetail } from './types';
import './styles/workbench.css';

export const App: React.FC = () => {
  const [activeNav, setActiveNav] = useState<NavItemKey>('overview');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskDetail[]>([]);

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

  // Load recent tasks on mount & when new tasks are selected
  useEffect(() => {
    if (taskDetail) {
      setRecentTasks((prev) => {
        const exists = prev.some((t) => t.task_id === taskDetail.task_id);
        if (exists) {
          return prev.map((t) => (t.task_id === taskDetail.task_id ? taskDetail : t));
        }
        return [taskDetail, ...prev];
      });
    }
  }, [taskDetail]);

  const handleTaskCreated = (taskId: string) => {
    setSelectedTaskId(taskId);
    setActiveNav('runs');
  };

  const handleSelectTaskFromOverview = (taskId: string) => {
    setSelectedTaskId(taskId);
    setActiveNav('runs');
  };

  return (
    <div className="cv-app-shell">
      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        activeItem={activeNav}
        onNavigate={(item) => setActiveNav(item)}
        onNewAgentClick={() => setActiveNav('runs')}
      />

      {/* 2. Main Content Wrapper */}
      <div className="cv-main-wrapper">
        {/* Top Header Bar */}
        <Header
          sovereignty={sovereignty}
          onOpenSystemLogs={() => setActiveNav('activity')}
          onDeployAgent={() => setActiveNav('runs')}
        />

        {/* Real-Time Perimeter Security Strip */}
        <PerimeterBanner sovereignty={sovereignty} />

        {/* Scrollable View Area */}
        <main className="cv-content-area">
          {/* View: Overview */}
          {activeNav === 'overview' && (
            <OverviewView
              sovereignty={sovereignty}
              recentTasks={recentTasks}
              onStartNewRun={() => setActiveNav('runs')}
              onViewAllRuns={() => setActiveNav('tasks')}
              onSelectTask={handleSelectTaskFromOverview}
              onConfigurePolicy={() => setActiveNav('policies')}
            />
          )}

          {/* View: Runs & Tasks (Workbench) */}
          {(activeNav === 'runs' || activeNav === 'tasks') && (
            <div className="cv-view-layout">
              <div className="cv-section-header-row">
                <div>
                  <h2 className="cv-section-title">Configure new agent run</h2>
                  <p className="cv-section-subtitle">
                    Define parameters and execution environment for the autonomous agent.
                  </p>
                </div>
              </div>

              {/* Two-Column Workbench Layout */}
              <div className="cv-workbench-grid">
                {/* Left Column: Task Creator */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <TaskCreator onTaskCreated={handleTaskCreated} disabled={isStreaming} />

                  {taskDetail && (
                    <TaskSummaryCard
                      task={taskDetail}
                      finalStatus={finalStatus}
                      onViewArtifacts={() => setActiveNav('artifacts')}
                    />
                  )}
                </div>

                {/* Right Column: Execution Preview & Environment Readiness */}
                <WorkbenchSidePanels
                  activeNode={activeNode}
                  completedNodes={completedNodes}
                  finalStatus={finalStatus}
                  sovereignty={sovereignty}
                  isStreaming={isStreaming}
                />
              </div>

              {/* 8-Stage Pipeline Visualizer (When task active or present) */}
              <GraphVisualizer
                activeNode={activeNode}
                completedNodes={completedNodes}
                iteration={iteration}
                maxIterations={maxIterations}
                finalStatus={finalStatus}
                isStreaming={isStreaming}
              />

              {/* Real-time SSE Live Event Stream */}
              <LiveEventFeed
                events={events}
                isStreaming={isStreaming}
                reconnectCount={reconnectCount}
              />
            </div>
          )}

          {/* View: Agents (Hero Workflows) */}
          {activeNav === 'agents' && (
            <HeroFlowLauncher
              onOpenInWorkbench={(taskId) => {
                setSelectedTaskId(taskId);
                setActiveNav('runs');
              }}
            />
          )}

          {/* View: Activity (SSE Live Feed dedicated view) */}
          {activeNav === 'activity' && (
            <div className="cv-view-layout">
              <div className="cv-section-header-row">
                <div>
                  <h2 className="cv-section-title">Operational Activity Stream</h2>
                  <p className="cv-section-subtitle">
                    Continuous SSE stream logs and internal agent node state telemetry.
                  </p>
                </div>
              </div>

              <LiveEventFeed
                events={events}
                isStreaming={isStreaming}
                reconnectCount={reconnectCount}
              />
            </div>
          )}

          {/* View: Tools */}
          {activeNav === 'tools' && <ToolsView />}

          {/* View: Models */}
          {activeNav === 'models' && <ModelsView />}

          {/* View: Sources (Vision & Documents) */}
          {activeNav === 'sources' && <VisionInspector />}

          {/* View: RAG & Artifacts */}
          {(activeNav === 'rag' || activeNav === 'artifacts') && (
            <ArtifactExplorer />
          )}

          {/* View: Security & Sovereignty */}
          {activeNav === 'security' && <SovereigntyDashboard />}

          {/* View: Policies, Audit & Settings */}
          {(activeNav === 'policies' || activeNav === 'audit' || activeNav === 'settings' || activeNav === 'support') && (
            <GovernanceView
              sovereignty={sovereignty}
              mode={activeNav === 'audit' ? 'audit' : activeNav === 'policies' ? 'policies' : 'settings'}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;