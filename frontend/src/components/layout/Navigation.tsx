import React from 'react';
import { IconCpu, IconEye, IconFileText, IconShield, IconZap } from '../common/Icons';

export type TabKey = 'workspace' | 'heroes' | 'vision' | 'sovereignty' | 'artifacts';

interface NavigationProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, onTabChange }) => {
  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'workspace', label: 'Agent Workbench', icon: <IconCpu size={16} /> },
    { key: 'heroes', label: 'Hero Flows', icon: <IconZap size={16} /> },
    { key: 'vision', label: 'Vision Inspector', icon: <IconEye size={16} /> },
    { key: 'sovereignty', label: 'Sovereignty & Security', icon: <IconShield size={16} /> },
    { key: 'artifacts', label: 'Deliverables & RAG', icon: <IconFileText size={16} /> },
  ];

  return (
    <nav className="wb-nav">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          className={`wb-nav-btn ${activeTab === tab.key ? 'active' : ''}`}
          onClick={() => onTabChange(tab.key)}
        >
          {tab.icon}
          {tab.label}
        </button>
      ))}
    </nav>
  );
};