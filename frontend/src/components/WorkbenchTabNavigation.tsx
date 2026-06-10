import React from 'react';
import type { TabType } from '../types';

interface WorkbenchTabNavigationProps {
  activeTab: TabType;
  onChange: (tab: TabType) => void;
}

const tabs: { id: TabType; label: string }[] = [
  { id: 'sample', label: '样例视频' },
  { id: 'material', label: '素材视频' },
  { id: 'result', label: '结果视频' },
];

export const WorkbenchTabNavigation: React.FC<WorkbenchTabNavigationProps> = ({ activeTab, onChange }) => {
  return (
    <div style={{
      display: 'flex',
      gap: 32,
      paddingLeft: 24,
      paddingRight: 24,
      paddingTop: 16,
      paddingBottom: 12,
      borderBottom: '1px solid var(--color-neutral-200)',
      backgroundColor: 'var(--color-neutral-100)',
    }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          style={{
            all: 'unset',
            cursor: 'pointer',
            fontSize: 15,
            fontWeight: 600,
            color: activeTab === tab.id ? 'var(--color-primary-500)' : 'var(--color-neutral-500)',
            paddingBottom: 10,
            borderBottom: activeTab === tab.id ? '2px solid var(--color-primary-500)' : '2px solid transparent',
            transition: 'all 0.2s',
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};
