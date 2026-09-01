import React, { useState } from 'react';
import {
  IconBell,
  IconChevronDown,
  IconSearch,
  IconShield,
  IconTerminal,
} from '../common/Icons';
import type { SovereigntyStatus } from '../../types';

interface HeaderProps {
  sovereignty: SovereigntyStatus | null;
  onOpenSystemLogs?: () => void;
  onDeployAgent?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSystemLogs, onDeployAgent }) => {
  const [workspace] = useState<string>('Workspace Switcher');
  const [searchValue, setSearchValue] = useState<string>('');

  return (
    <header className="cv-topbar">
      {/* Search Input Bar */}
      <div className="cv-search-wrapper">
        <IconSearch size={16} className="cv-search-icon" color="#4b5563" />
        <input
          type="text"
          className="cv-search-input"
          placeholder="Search resources..."
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
        />
      </div>

      {/* Workspace Switcher */}
      <div className="cv-workspace-switcher">
        <span className="cv-workspace-name">{workspace}</span>
        <IconChevronDown size={15} color="#4b5563" />
      </div>

      {/* Right Action Icons & Controls */}
      <div className="cv-topbar-actions">
        <button type="button" className="cv-icon-btn" title="Notifications" aria-label="Notifications">
          <IconBell size={18} color="#374151" />
        </button>
        <button
          type="button"
          className="cv-icon-btn"
          title="Terminal Logs"
          onClick={onOpenSystemLogs}
          aria-label="Terminal Logs"
        >
          <IconTerminal size={18} color="#374151" />
        </button>
        <button type="button" className="cv-icon-btn" title="Security Status" aria-label="Security Status">
          <IconShield size={18} color="#374151" />
        </button>

        <button
          type="button"
          className="cv-btn-header-secondary"
          onClick={onOpenSystemLogs}
        >
          System Logs
        </button>

        <button
          type="button"
          className="cv-btn-header-primary"
          onClick={onDeployAgent}
        >
          Deploy Agent
        </button>

        {/* User Profile Avatar */}
        <div className="cv-user-avatar" title="Administrator">
          <img
            src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'><rect width='32' height='32' fill='%23e5e7eb'/><circle cx='16' cy='12' r='5' fill='%234b5563'/><path d='M8 26c0-4.4 3.6-8 8-8s8 3.6 8 8' fill='%234b5563'/></svg>"
            alt="User"
            className="cv-avatar-img"
          />
        </div>
      </div>
    </header>
  );
};