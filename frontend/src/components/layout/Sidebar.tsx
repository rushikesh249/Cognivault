import React from 'react';
import {
  IconActivity,
  IconAgents,
  IconCompass,
  IconDatabase,
  IconFileCheck,
  IconFileText,
  IconHelpCircle,
  IconLayers,
  IconLock,
  IconOverview,
  IconPlus,
  IconSettings,
  IconShield,
  IconTasks,
  IconTools,
  IconZap,
} from '../common/Icons';

export type NavItemKey =
  | 'overview'
  | 'tasks'
  | 'agents'
  | 'runs'
  | 'activity'
  | 'tools'
  | 'models'
  | 'sources'
  | 'rag'
  | 'artifacts'
  | 'security'
  | 'policies'
  | 'audit'
  | 'settings'
  | 'support';

interface SidebarProps {
  activeItem: NavItemKey;
  onNavigate: (item: NavItemKey) => void;
  onNewAgentClick: () => void;
}

interface NavGroup {
  label: string;
  items: {
    key: NavItemKey;
    label: string;
    icon: React.ReactNode;
    badge?: string;
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({ activeItem, onNavigate, onNewAgentClick }) => {
  const groups: NavGroup[] = [
    {
      label: 'Workspace',
      items: [
        { key: 'overview', label: 'Overview', icon: <IconOverview size={18} /> },
        { key: 'tasks', label: 'Tasks', icon: <IconTasks size={18} /> },
        { key: 'agents', label: 'Agents', icon: <IconAgents size={18} /> },
        { key: 'runs', label: 'Runs', icon: <IconZap size={18} /> },
      ],
    },
    {
      label: 'Operations',
      items: [
        { key: 'activity', label: 'Activity', icon: <IconActivity size={18} /> },
        { key: 'tools', label: 'Tools', icon: <IconTools size={18} /> },
        { key: 'models', label: 'Models', icon: <IconCompass size={18} /> },
      ],
    },
    {
      label: 'Knowledge',
      items: [
        { key: 'sources', label: 'Sources', icon: <IconDatabase size={18} /> },
        { key: 'rag', label: 'RAG', icon: <IconLayers size={18} /> },
        { key: 'artifacts', label: 'Artifacts', icon: <IconFileText size={18} /> },
      ],
    },
    {
      label: 'Governance',
      items: [
        { key: 'security', label: 'Security', icon: <IconShield size={18} /> },
        { key: 'policies', label: 'Policies', icon: <IconLock size={18} /> },
        { key: 'audit', label: 'Audit', icon: <IconFileCheck size={18} /> },
      ],
    },
  ];

  return (
    <aside className="cv-sidebar">
      {/* Brand / Logo Header */}
      <div className="cv-sidebar-brand" onClick={() => onNavigate('overview')} role="button" tabIndex={0}>
        <div className="cv-brand-icon-wrap">
          <IconShield size={19} color="#ffffff" />
        </div>
        <div className="cv-brand-info">
          <div className="cv-brand-title">COGNIVAULT</div>
          <div className="cv-brand-subtitle">Sovereign AI Ops</div>
        </div>
      </div>

      {/* Primary Action Button: + New Agent */}
      <div className="cv-sidebar-cta">
        <button
          type="button"
          className="cv-btn-new-agent"
          onClick={onNewAgentClick}
          id="btn-new-agent"
        >
          <IconPlus size={17} />
          <span>New Agent</span>
        </button>
      </div>

      {/* Nav Groups Menu */}
      <div className="cv-sidebar-nav">
        {groups.map((grp) => (
          <div key={grp.label} className="cv-nav-group">
            <div className="cv-nav-group-label">{grp.label}</div>
            <div className="cv-nav-group-list">
              {grp.items.map((item) => {
                const isActive = activeItem === item.key;
                return (
                  <button
                    key={item.key}
                    type="button"
                    className={`cv-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => onNavigate(item.key)}
                  >
                    <span className="cv-nav-icon">{item.icon}</span>
                    <span className="cv-nav-text">{item.label}</span>
                    {item.badge && <span className="cv-nav-badge">{item.badge}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Sidebar Footer System Items */}
      <div className="cv-sidebar-footer">
        <button
          type="button"
          className={`cv-nav-item ${activeItem === 'settings' ? 'active' : ''}`}
          onClick={() => onNavigate('settings')}
        >
          <span className="cv-nav-icon"><IconSettings size={18} /></span>
          <span className="cv-nav-text">Settings</span>
        </button>
        <button
          type="button"
          className={`cv-nav-item ${activeItem === 'support' ? 'active' : ''}`}
          onClick={() => onNavigate('support')}
        >
          <span className="cv-nav-icon"><IconHelpCircle size={18} /></span>
          <span className="cv-nav-text">Support</span>
        </button>
      </div>
    </aside>
  );
};
