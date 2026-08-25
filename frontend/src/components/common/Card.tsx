import React from 'react';

interface CardProps {
  title?: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({ title, icon, badge, children, className = '', style }) => {
  return (
    <div className={`wb-card ${className}`} style={style}>
      {title && (
        <div className="wb-card-header">
          <div className="wb-card-title">
            {icon && <span>{icon}</span>}
            {title}
          </div>
          {badge && <div>{badge}</div>}
        </div>
      )}
      {children}
    </div>
  );
};